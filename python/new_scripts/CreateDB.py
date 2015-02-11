#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, logging
from utils import *

def main(opts):
    # Set logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, opts.log.upper()))
    
    connectionString = postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, True)
    
    os.system('createdb ' + connectionString)

    #os.system('psql ' + connectionString + ' -c "CREATE EXTENSION POSTGIS;"')
    #os.system('psql ' + connectionString + ' -f ' + opts.sql)
    
    connection = psycopg2.connect(postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()

    cursor.execute("CREATE EXTENSION POSTGIS")
    connection.commit()

    old_isolation_level = connection.isolation_level
    connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    cursor.execute(open(opts.sql,"r").read())
    connection.set_isolation_level(old_isolation_level)
    
    cursor.execute("select tablename from  pg_tables where schemaname = 'public'")
    tablesNames = cursor.fetchall()
    for (tableName,) in tablesNames:
        cursor.execute('GRANT SELECT ON ' + tableName + ' TO public')

    for tableName in ('ITEM', 'ITEM_OBJECT', 'OSG_LOCATION', 'OSG_LABEL', 'OSG_CAMERA', 'OSG_ITEM_CAMERA', 'OSG_ITEM_OBJECT'):
        cursor.execute( 'GRANT SELECT,INSERT,UPDATE,DELETE ON ' + tableName + ' TO public')
    
    connection.commit()
    connection.close()
    
if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Create the DB"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-f','--sql',default='',help='File with the SQL commands to create the DB',type='string')
    op.add_option('-d','--dbname',default=DEFAULT_DB,help='Postgres DB name [default ' + DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=USERNAME,help='DB user [default ' + USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-b','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-l','--log',help='Logging level (choose from ' + ','.join(LOG_LEVELS) + ' ; default ' + DEFAULT_LOG_LEVEL + ')',type='choice', choices=['debug', 'info', 'warning', 'error','critical'], default=DEFAULT_LOG_LEVEL)
    (opts, args) = op.parse_args()
    main(opts)
