#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, time, re, subprocess, glob
import utils

DEFAULT_SITES_TABLE = 'sites_geoms'
DEFAULT_SITES_ID_COLUMN = 'site_id'
DEFAULT_SITES_GEOM_COLUMN = 'geom'

def main(opts):
    t0 = time.time()
    # Check options
    for option in (opts.siteid, opts.output):
        if option == '':
            print 'ERROR - missing options: Please specify (at least) site ID and output LAS file'
            return
        
    # Define connection string (to be used by python connection wrapper (psycopg2)
    # and also command-line required to export to ASCII
    connString = utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False)
    
    # Create python postgres connection
    connection = psycopg2.connect(connString)
    cursor = connection.cursor()
    # Check if the site id is found in the DB
    siteid = int(opts.siteid)

    aux = 'ch'
    if opts.buffer != '0':
        aux = 'ST_Buffer(ch,' + opts.buffer + ')'
    aux = 'ST_Envelope(' + aux + ')'

    query = 'select st_astext(ch), st_xmin(ebch), st_xmax(ebch), st_ymin(ebch), st_ymax(ebch) from (select ch, ' + aux + ' as ebch from (select ST_ConcaveHull(' + opts.sitesgeomcolumn + ', ' + opts.concave + ') as ch from ' + opts.sites + ' where ' + opts.sitesidcolumn + ' = %s) A) B'
    queryArgs = [siteid,]
 
    print cursor.mogrify(query, queryArgs)
    cursor.execute(query, queryArgs)     
    row = cursor.fetchone()
    if row == None:
        print 'ERROR - wrong site id: No site is found with specified site id'
        return
    (concaveHull, minx, maxx, miny, maxy) = row
 
    # If it is found we extract the individual 2D points of the vertices
    points = []
    for e in concaveHull.split(','):
        c = re.findall("\d+.\d+ \d+.\d+",e)
        points.append(c[0].split(' '))
    
    tfilename = opts.output + '.list' 
    tfile = open(tfilename, 'w')
    for f in glob.glob(opts.lasfolder + '/*las') + glob.glob(opts.lasfolder + '/*laz'):
        tfile.write(f + '\n')
    tfile.close()
    command = 'lasmerge -lof ' + tfilename + ' -inside ' + str(minx) + ' ' + str(miny) + ' ' + str(maxx) + ' ' + str(maxy) + ' -o ' + opts.output
    print command
    os.system(command)
    os.system('rm ' + tfilename)
    statcommand = "lasinfo -i " + opts.output + " -nv -nmm -histo z 10000000"
    lines  = '\n'.join(subprocess.Popen(statcommand, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()).split('\n')
    avgZ = 0
    numpoints = None
    for line in lines:
        if line.count('average z'):
             avgZ = float(line.split()[-1])
        if line.count('number of point records:'):
             numpoints = int(line.split()[-1])
    
    footoutput = opts.output + '_footprint.csv' 
    print 'Creating footprint CSV ' + footoutput + '...'
    fpOutput = open(footoutput, 'w')
    for point in points:
        point.append(str(avgZ))
        fpOutput.write(','.join(point) + '\n')
    fpOutput.close()
    
    print 'Finished!. Time:', time.time() - t0, '#Points:' , numpoints


if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Creates a LAS/LAZ file containing the cutout of the points in the bounding box of an area delimited by the footprint of a site.\nIt is possible to specify a buffer around the footprint.\nIt also outputs an auxiliary ASCII file with the vertices of the footprint (for the z value we use the average of the z coordinates of the cutout LAS/LAZ file"

    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--siteid',default='',help='Site ID',type='string')
    op.add_option('-x','--concave',default='0.9',help='Target percentage of concavity used by PostGIS when unifying the multipolygons [default 0.9]. Must be between 0 and 1 (1 is a convex hull)',type='string')
#    op.add_option('-n','--dbname',default=utils.DEFAULT_DB,help='DB name [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-n','--dbname',default='pattydb',help='DB name [default pattydb]',type='string')
    op.add_option('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-m','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-s','--sites',default=DEFAULT_SITES_TABLE,help='Sites table [default ' + DEFAULT_SITES_TABLE + ']',type='string')
    op.add_option('-t','--sitesgeomcolumn',default=DEFAULT_SITES_GEOM_COLUMN,help='Geometry column in sites table [default ' + DEFAULT_SITES_GEOM_COLUMN + ']',type='string')
    op.add_option('-d','--sitesidcolumn',default=DEFAULT_SITES_ID_COLUMN,help='ID column in sites table [default ' + DEFAULT_SITES_ID_COLUMN + ']',type='string')
    op.add_option('-o','--output',default='',help='Output LAS/LAZ file',type='string')
    op.add_option('-f','--buffer',default='0',help='Buffer around the footprint [default 0]',type='string')
    op.add_option('-a','--lasfolder',default=utils.DEFAULT_BACKGROUND_FOLDER,help='Folder that contains the LAS/LAZ files [default ' + utils.DEFAULT_BACKGROUND_FOLDER + ']',type='string')
    (opts, args) = op.parse_args()
    main(opts)
