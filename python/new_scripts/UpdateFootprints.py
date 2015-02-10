#!/usr/bin/env python
################################################################################
# Description:      Script to update the sites footprints in the DB 
#                   which are imported from an sql file (another DB dump)
# Author:           Elena Ranguelova, NLeSc, E.Ranguelova@nlesc.nl                                       
# Creation date:    22.01.2015      
# Modification date: 09.02.2015
# Modifications:   
# Notes:            Based on mergefootprints.py from the PattyFFW Oct 2014
################################################################################
import os, argparse, utils
import psycopg2

logger = None
connection = None
cursor = None

# CONSTANTS
LOG_FILENAME = 'UpdateFootprints.log'

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to update the sites footprints from an SQL file to the DB")
    parser.add_argument('-i','--input',help='Input SQL file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name which should be updated with these footprints ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=True)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=True)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
        
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args() 
            
    return args

def clean_temp_table(args):
    
    drop_table_sql = "DROP TABLE IF EXISTS sites_geoms_temp" 
    utils.dbExecute(cursor, drop_table_sql)
    
    msg = 'Removed table sites_geoms_temp (if existed).'
    print msg
    logger.info(msg)
    
def load_sql_file(args):
    success = False
    
    # set the level temporarily to autocommit
 #   old_isolation_level = connection.isolation_level
    connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    #local_cursor = connection.cursor()
    # execute the SQL statement from the external DBdump of site object geometries
    try:    
    #    local_cursor.execute(open(args.input,"r").read())
        cursor.execute(open(args.input,"r").read())
    except Exception, E:
        err_msg = 'Cannot execute the commands in %s.'%args.input
        print(err_msg)
        logger.error(err_msg)
        logger.error(" %s: %s" % (E.__class__.__name__, E))
        raise
        
    success = True
    msg = 'Successful execution of the commands in %s.'%args.input
    print msg
    logger.debug(msg)
        
    #local_cursor.close()  
    
    # retun back the old level
#    connection.set_isolation_level(old_isolation_level)


    return success
#------------------------------------------------------------------------------        
def run(args): 
    
    global logger
    global connection
    global cursor
    
    # start logging
    logger = utils.start_logging(filename=LOG_FILENAME, level=utils.DEFAULT_LOG_LEVEL)
    localtime = utils.getCurrentTimeAsAscii()
    msg = 'UpdateFoorptints scipt logging starts at %s.' %localtime
    print msg
    logger.info(msg)

    # start timer
    t0 = utils.getCurrentTime()
    
    if os.popen('head -500 ' + args.input + ' | grep "CREATE TABLE sites_geoms_temp"').read().count("CREATE TABLE sites_geoms_temp") == 0:
        logger.error("The table in the SQL file must be named sites_geom_temp. Replace the table name to sites_geoms_temp!")
        return  
     
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 
        
    # clean the temp table if exsisted
    clean_temp_table(args)

    # load the table sites_geoms_temp from the SQL file ot the DB
    success_loading = load_sql_file(args)
        
    if success_loading:

        # get the union geometry inside the SQL file
        select_geom_sql = "SELECT site_id as site_id, ST_Multi(ST_Transform( ST_Union( geom ), " + str(utils.SRID) + " )) AS geom FROM sites_geoms_temp GROUP BY site_id"
        values, num_geoms = utils.fetchDataFromDB(cursor, select_geom_sql)
        
        # check if the SITES table is empty, then change the type of the geom field
        num_items = utils.countElementsTable(cursor, 'item')
        print "Number of elements in item table: %s" %num_items        
        
#        select_geom_sql = "SELECT geom FROM item"
#        values, num_geoms = utils.fetchDataFromDB(cursor, select_geom_sql)
#
#        print cursor.description
#        type_code  = cursor.description[0].type_code
#        print type_code
#        
#        select_type_sql = "SELECT typname FROM pg_type WHERE OID=%s"%type_code
#        values, num_geoms = utils.fetchDataFromDB(cursor, select_type_sql)
#        
#        print values[0]
        
        col_type = utils.typeColumnTable(cursor, 'geom','item')
        print col_type
        
      
#        check_query = "SELECT COUNT(*) FROM site"
#        utils.dbExecute(cursor, check_query)    
#        num_items = cursor.fetchone()
#        
# #       insert_sql_bunch = "INSERT INTO site(site_id, geom) VALUES(values)" # is this correct!???
# #       insert_sql_missing = "INSERT INTO site(site_id, geo) VALUES(site_id_values, geom_value)"
# #       update_sql = "UPDATE TABLE site SET geom = geom_value WHERE site_id = site_id_value"
#        
#        if (num_items == 0): # alter the geometry field type
#             # shall we read this from utils!?? Is it a fixed thing!?
#            alter_type_sql = "ALTER TABLE site ALTER COLUMN geom TYPE geometry(MultiPolygon, " + str(utils.SRID) + ")"            
#            utils.dbExecute(cursor, alter_type_sql)
#            
#       # else: # merge the data from the sites_geom_table (filled from the input SQL file) into the DB
#            #if the DB has no overlap with the entries from the sites_geoms_temp
#            # if the DB has overlap with the entries from the sites_geoms_temp
    
        # clean the temp table
        clean_temp_table(args)         
    # close the conection to the DB
    utils.closeConnectionDB(connection, cursor)
    
    # measure elapsed time
    elapsed_time = utils.getCurrentTime() - t0    
    msg = 'Finished. Total elapsed time: %s s.' %elapsed_time
    print(msg)
    logger.info(msg)
    
    # end logging
    localtime = utils.getCurrentTimeAsAscii()  
    msg = 'UpdateFootprints script logging ends at %s'% localtime
    print(msg)
    logger.info(msg)
    
    return




if __name__ == '__main__':
    run( apply_argument_parser() )