#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, time, re, multiprocessing, glob
import utils

DEFAULT_SITES_TABLE = 'sites_geoms'
DEFAULT_SITES_ID_COLUMN = 'site_id'
DEFAULT_SITES_GEOM_COLUMN = 'geom'
DEFAULT_BLOCKS_COLUMN = 'pa'
BLOCKS_ID = 'id'

def runChild(minCandidateIndex, maxCandidateIndex, candidatesTable, connString, resultTable, tempGeomTable, siteid):
    connection = psycopg2.connect(connString)
    cursor = connection.cursor()
    query = """
INSERT INTO """ + resultTable + """ ( x,y,z,Red,Green,Blue ) 
    SELECT PC_Get(qpoint, 'x') as x, PC_Get(qpoint, 'y') as y, PC_Get(qpoint, 'z') as z, PC_Get(qpoint, 'Red') AS Red, PC_Get(qpoint, 'Green') AS Green, PC_Get(qpoint, 'Blue') AS Blue FROM (
        SELECT pc_explode(pc_intersection(pa,geom)) as qpoint from """ + candidatesTable + ', ' + tempGeomTable + """ 
            WHERE """ + tempGeomTable + ".id = %s AND " + candidatesTable + ".id >= %s AND " + candidatesTable + ".id < %s) as T"
            
    queryArgs = [siteid, minCandidateIndex, maxCandidateIndex]
    cursor.execute(query, queryArgs)
    connection.commit()
    cursor.close()
    connection.close()


def main(opts):
    t0 = time.time()
    # Check options
    for option in (opts.dbuser, opts.siteid, opts.output):
        if option == '':
            print 'ERROR - missing options: Please specify (at least) DB user, site ID and output LAS file'
            return
        
    if opts.lastools and not opts.square:
        print 'ERROR - lastools only available if square approximation is selected'
        return
    
    # Define connection string (to be used by python connection wrapper (psycopg2)
    # and also command-line required to export to ASCII
    connString = utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False)
    
    # Create python postgres connection
    connection = psycopg2.connect(connString)
    cursor = connection.cursor()
    
    # Check if the site id is found in the DB
    siteid = int(opts.siteid)
    cursor.execute('select st_astext(' + opts.sitesgeomcolumn + ') from ' + opts.sites + ' where ' + opts.sitesidcolumn + '=%s', [siteid,])
    row = cursor.fetchone()
    if row == None:
        print 'ERROR - wrong site id: No site is found with specified site id'
        return
    
    # If it is found we extract the individual 2D points of the vertices
    points = []
    for e in row[0].split(','):
        c = re.findall("\d+.\d+ \d+.\d+",e)
        points.append(c[0].split(' '))
    
    # Table for query geometries for current user
    tempGeomTable = 'RESULTS.' + opts.dbuser + '_temp_geom'
    cursor.execute("select exists(select * from information_schema.tables where table_name=%s)", (tempGeomTable.split('.')[-1], ))
    if cursor.fetchone()[0]:
        # If it is there we delete previous geom for current site
        cursor.execute("DELETE FROM " + tempGeomTable + " WHERE id = %s", [siteid,])
    else:
        # Create table if not there
        cursor.execute("CREATE TABLE " +  tempGeomTable + " (id integer, geom public.geometry(Geometry," + str(utils.SRID) + "))")
    connection.commit()
    
    qgeom = opts.sitesgeomcolumn
    if opts.buffer != '0':
        qgeom = 'ST_Buffer(' + opts.sitesgeomcolumn + ',' + opts.buffer + ')'
    if opts.square:
        qgeom = 'ST_Envelope(' + qgeom + ')'
    
    cursor.execute('INSERT INTO ' + tempGeomTable + ' SELECT ' + opts.sitesidcolumn + ', ' + qgeom + ' FROM ' + opts.sites + ' WHERE ' + opts.sitesidcolumn + ' = %s', [siteid,])
    connection.commit()
    
    if opts.lastools:
        tq0 = time.time()
        cursor.execute('select st_xmin(geom), st_xmax(geom), st_ymin(geom), st_ymax(geom) from ' + tempGeomTable + ' where id = %s', [siteid,])
        (minx,maxx,miny,maxy) = cursor.fetchone()
        tfilename = opts.output + '.list' 
        tfile = open(tfilename, 'w')
        for f in glob.glob(opts.lasfolder + '/*las') + glob.glob(opts.lasfolder + '/*laz'):
            tfile.write(f + '\n')
        tfile.close()
        command = 'lasmerge -lof ' + tfilename + ' -inside ' + str(minx) + ' ' + str(miny) + ' ' + str(maxx) + ' ' + str(maxy) + ' -o ' + opts.output
        print command
        os.system(command)
        os.system('rm ' + tfilename)
        
        (numpoints, minX, minY, minZ, maxX, maxY, maxZ, scaleX, scaleY, scaleZ, offsetX, offsetY, offsetZ) = utils.getLASParams(opts.output, tool = 'lastools')
        
        avgZ = sum((float(minZ), float(maxZ))) / 2.

        print 'Time:', time.time() - tq0, '  ', '#points:', numpoints
    else:
    
        resultTable = 'RESULTS.' + opts.dbuser + '_temp_site_' + opts.siteid
        cursor.execute("select exists(select * from information_schema.tables where table_name=%s)", (resultTable.split('.')[-1], ))
        if cursor.fetchone()[0]:
            cursor.execute('DROP TABLE ' + resultTable)
            connection.commit()
    
        numproc = int(opts.cores)
        
        print 'Querying PC for site ' + opts.siteid + '...'
        tq0 = time.time()
        if numproc == 1:
            query = """
    CREATE TABLE """  + resultTable + """ AS (
        SELECT PC_Get(qpoint, 'x') AS x, PC_Get(qpoint, 'y') AS y, PC_Get(qpoint, 'z') AS z, PC_Get(qpoint, 'Red') AS Red, PC_Get(qpoint, 'Green') AS Green, PC_Get(qpoint, 'Blue') AS Blue from (
            SELECT pc_explode(pc_intersection(""" + opts.blockscolumn + """,geom)) AS qpoint from """ + opts.blocks + """, """ + tempGeomTable + """ 
                WHERE pc_intersects(""" + opts.blockscolumn + """,geom) and """ + tempGeomTable + """.id = %s) AS qtable)"""
        
            #print cursor.mogrify(query, [siteid, ])
            cursor.execute(query, [siteid, ])
            numpoints = int(cursor.statusmessage.split(' ')[-1])
        else:
            candidatesTable = 'RESULTS.query_candidates_' + opts.dbuser
            
            # First we get the candidates
            cursor.execute("select exists(select * from information_schema.tables where table_name=%s)", (candidatesTable.split('.')[-1], ))
            if cursor.fetchone()[0]:
                cursor.execute('DROP TABLE ' + candidatesTable)
                connection.commit()
                
            query = """
    CREATE TABLE """  + candidatesTable + """ AS 
        SELECT ROW_NUMBER() over (order by """ + opts.blocks  +""".""" + BLOCKS_ID + """) as id, """ + opts.blockscolumn + """ FROM """ + opts.blocks +""", """+tempGeomTable+ """ 
        WHERE pc_intersects(""" + opts.blockscolumn + """,geom) AND """+tempGeomTable+""".id = %s
    """ 
             #print cursor.mogrify(query, [siteid, ])
            cursor.execute(query, [siteid, ])
            numcandidates = int(cursor.statusmessage.split(' ')[-1])
            connection.commit()
            cursor.execute("CREATE INDEX " + candidatesTable.split('.')[-1] + "_id_idx ON " + candidatesTable + "(id);")
            connection.commit()
    	#TODO: try double preciosion (x,y,z) and integers (rgb)
            cursor.execute("""
    CREATE TABLE """ + resultTable + """ (
                    x NUMERIC,
                    y NUMERIC,
                    z NUMERIC,
                    Red NUMERIC,
                    Green NUMERIC,
                    Blue NUMERIC
                );""")
            connection.commit()
            n = numcandidates / numproc
            m = numcandidates - (numproc * n)
            index = 1
            children = []
            for i in range(numproc):
                newindex = index + n
                if i < m:
                    newindex += 1
                children.append(multiprocessing.Process(target=runChild, 
                    args=(index, newindex,candidatesTable, connString, resultTable, tempGeomTable, siteid,)))
                children[-1].start()  
                index = newindex
            # wait for all children to finish their execution
            for i in range(numproc):
                children[i].join()
            cursor.execute('select count(x) from ' + resultTable)
            
            numpoints = int(cursor.fetchall()[0][0])
        print 'Time:', time.time() - tq0, '  ', '#points:', numpoints
        connection.commit()

        if numpoints:
       
            tempFile = "temp_" + resultTable + ".csv"
            
            connString= connString = utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, True)
            print 'Creating PC LAS ' + opts.output + '...'
            os.system('psql ' + connString +  ' -c "COPY ' + resultTable + ' to STDOUT DELIMITER \',\'" > ' + tempFile)       
            c = "txt2las -parse xyzRGB " + tempFile + " -o " + opts.output
            os.popen(c)
    
            os.system('rm ' + tempFile)
    
            cursor.execute('select avg(z) from '  + resultTable)
            avgZ = cursor.fetchone()[0]
            #    cursor.execute('DROP TABLE ' + resultTable)
            connection.commit()
            connection.close()
    
    if avgZ != None:
        footoutput = "footprint_" + opts.output + '.csv'
        print 'Creating footprint CSV ' + footoutput + '...'
        fpOutput = open(footoutput, 'w')
        for point in points:
            point.append(str(avgZ))
            fpOutput.write(','.join(point) + '\n')
        fpOutput.close()
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Creates a LAS/LAZ file containing the points in an area delimited by the footprint of a site.\nIt is possible to specify a buffer around the footprint.\nIt also outputs an auxiliary ASCII file with the vertices of the footprint (for the z value we use the average of the z coordinates of the main LAS/LAZ file)"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--siteid',default='',help='Site ID',type='string')
    op.add_option('-n','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name where to store the geometries [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=username,help='DB user [default ' + username + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-m','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-s','--sites',default=DEFAULT_SITES_TABLE,help='Sites table [default ' + DEFAULT_SITES_TABLE + ']',type='string')
    op.add_option('-t','--sitesgeomcolumn',default=DEFAULT_SITES_GEOM_COLUMN,help='Geometry column in sites table [default ' + DEFAULT_SITES_GEOM_COLUMN + ']',type='string')
    op.add_option('-d','--sitesidcolumn',default=DEFAULT_SITES_ID_COLUMN,help='ID column in sites table [default ' + DEFAULT_SITES_ID_COLUMN + ']',type='string')
    op.add_option('-b','--blocks',default=utils.DEFAULT_BACKGROUND,help='Point cloud (blocks) table [default ' + utils.DEFAULT_BACKGROUND + ']',type='string')
    op.add_option('-l','--blockscolumn',default=DEFAULT_BLOCKS_COLUMN,help='Block column in blocks table [default ' + DEFAULT_BLOCKS_COLUMN + ']',type='string')
    op.add_option('-o','--output',default='',help='Output LAS/LAZ file',type='string')
    op.add_option('-f','--buffer',default='0',help='Buffer around the footprint [default 0]',type='string')
    op.add_option('-q','--square', action="store_true", default=False, help="Approximate query area to a square")
    op.add_option('-c','--cores',default='1',help='Number of cores to be used in query [default 1]',type='string')
    op.add_option('-x','--lastools', action="store_true", default=False, help="It uses lastools to get the filtered points (only possible if using square approximation")
    op.add_option('-a','--lasfolder',default=utils.DEFAULT_BACKGROUND_FOLDER,help='Folder that contains the LAS/LAZ files [default ' + utils.DEFAULT_BACKGROUND_FOLDER + ']',type='string')
    (opts, args) = op.parse_args()
    main(opts)
