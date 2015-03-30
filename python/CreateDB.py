#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, argparse, logging, time, utils

def run(opts):
    # Set logging
    #logname = os.path.splitext(os.path.basename(opts.sql))[0] + '.log'
    logname = os.path.basename(opts.sql) + '.log'
    utils.start_logging(filename=logname, level=opts.log)
   
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


def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Create the DB")
    parser.add_argument('-f','--sql',default='',help='File with the SQL commands to create the DB',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name [default ' + utils.DEFAULT_DB + ']',type=str)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str)
    parser.add_argument('-b','--dbhost',default='',help='DB host',type=str)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str)
    parser.add_argument('--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    return parser

if __name__ == "__main__":
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
