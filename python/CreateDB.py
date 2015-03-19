#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse,logging, time, utils

def main(opts):
    # Set logging
    logname = os.path.basename(opts.sql) + '.log'
    utils.start_logging(filename=logname, level=opts.log)
    utils.checkSuperUser()
   
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' %localtime
    print msg
    logging.info(msg)
    os.system('createdb ' + utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, True))
    
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport) 

    msg = 'Adding PostGIS extension'
    logging.info(msg)
    #print msg
    cursor.execute("CREATE EXTENSION POSTGIS")
    connection.commit()

    success_loading = utils.load_sql_file(cursor, opts.sql)
 
    msg = 'Granting relevant permissions' 
    logging.info(msg)
    #print msg

    if success_loading:    
        cursor.execute("select tablename from  pg_tables where schemaname = 'public'")
        tablesNames = cursor.fetchall()
        for (tableName,) in tablesNames:
            cursor.execute('GRANT SELECT ON ' + tableName + ' TO public')
    
        for tableName in ('ITEM', 'ITEM_OBJECT', 'OSG_LOCATION', 'OSG_LABEL', 'OSG_CAMERA', 'OSG_ITEM_CAMERA', 'OSG_ITEM_OBJECT'):
            cursor.execute( 'GRANT SELECT,INSERT,UPDATE,DELETE ON ' + tableName + ' TO public')
    
        connection.commit()
        connection.close()
    
    msg = 'Finished. Total elapsed time  %.02f seconds. See %s' % ((time.time() - t0), logname)
    logging.info(msg)
    print msg


if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Create the DB"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-f','--sql',default='',help='File with the SQL commands to create the DB',type='string')
    op.add_option('-d','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-b','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-l','--log',help='Logging level (choose from ' + ','.join(utils.LOG_LEVELS_LIST) + ' ; default ' + utils.DEFAULT_LOG_LEVEL + ')',type='choice', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    (opts, args) = op.parse_args()
    main(opts)
