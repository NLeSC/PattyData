#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=logging.DEBUG)
import utils 
        
def main(opts):
    if opts.input == '':
        logging.error('specify input file!')
        return
    # Check that beginning of the file does not contain a create database statement
    if os.popen('head -500 ' + opts.input + ' | grep "CREATE TABLE sites_geoms_temp"').read().count("CREATE TABLE sites_geoms_temp") == 0:
        logging.error("The table in the SQL file must be named sites_geom_temp. Replace the table name to sites_geoms_temp")
        return    
     
    # Establish connection with DB
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    # We load the new file
    connParams = utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, True)
    logFile = opts.input + '.log'
    command = 'psql ' + connParams + ' -f ' + opts.input + ' &> ' + logFile
    logging.info(command)
    os.system(command)
    
    #Check errors
    if os.popen('cat ' + logFile + ' | grep ERROR').read().count("ERROR"):
        logging.error('There was some errors in the data loading. Please see log ' + logFile)
    else:
        cursor.execute("TRUNCATE TABLE sites_geoms")
        connection.commit()
        cursor.execute("ALTER TABLE sites_geoms ALTER COLUMN geom TYPE geometry(MultiPolygon," + str(utils.SRID) + ")")
        connection.commit()
        #cursor.execute("insert into sites_geoms select site_id,st_astext(geom) from (select site_id, geom, row_number() over (partition by site_id) as rownum from sites_geom_temp) tmp where rownum < 2")
        cursor.execute("INSERT INTO sites_geoms( site_id, geom ) SELECT site_id as site_id, ST_Multi(ST_Transform( ST_Union( geom ), " + str(utils.SRID) + " )) AS geom FROM sites_geoms_temp GROUP BY site_id")
        
        connection.commit()
        cursor.execute("DROP TABLE sites_geoms_temp")
        connection.commit()
        
if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Merges Footprints file (SQL) with ViaAppia DB"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--input',default='',help='SQL file with SQL footprints',type='string')
#    op.add_option('-d','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name where to store the geometries [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-d','--dbname',default='temppattydb',help='Postgres DB name where to store the geometries [default temppattydb]',type='string')
    op.add_option('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    (opts, args) = op.parse_args()
    main(opts)
