#!/usr/bin/env python
################################################################################
# Description:      Script to update the sites footprints in the DB 
#                   which are imported from an sql file (another DB dump)
# Author:           Elena Ranguelova, NLeSc, E.Ranguelova@nlesc.nl                                       
# Creation date:    22.01.2015      
# Modification date:
# Modifications:   
# Notes:            Based on mergefootprints.py from the PattyFFW Oct 2014
################################################################################
import os, argparse, utils, logging

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

def load_sql_file(args):
    success = False
    
    connParams = utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, True)
    logFile = args.input + '.log'
    command = 'psql ' + connParams + ' -f ' + args.input + ' &> ' + logFile
    logging.info(command)
    os.system(command) 
    
    if os.popen('cat ' + logFile + ' | grep ERROR').read().count("ERROR"):
        msg  = 'There was some errors in the data loading. Please see log ' + logFile
        print msg
        logging.error(msg)
    else:
        success = True    
    
    return success
#------------------------------------------------------------------------------        
def run(args): 
    
    if os.popen('head -500 ' + args.input + ' | grep "CREATE TABLE sites_geoms_temp"').read().count("CREATE TABLE sites_geoms_temp") == 0:
        logging.error("The table in the SQL file must be named sites_geom_temp. Replace the table name to sites_geoms_temp")
        return  
        
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport)  
    
    # load the table sites_geoms_temp from the SQL file ot the DB
    success_loading = load_sql_file(args)
    
#    if success_loading:
#        
#        # get the union geometry inside the SQL file
#        select_geom_sql = "SELECT site_id as site_id, ST_Multi(ST_Transform( ST_Union( geom ), " + str(utils.SRID) + " )) AS geom FROM sites_geoms_temp GROUP BY site_id"
#        values, num_geoms = utils.dbExecute(cursor, select_geom_sql)
#        
#        # check if the SITES table is empty, then change the type of the geom field
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
                    
    # close the conection to the DB
    utils.closeConnectionDB(connection, cursor)
    
    return




if __name__ == '__main__':
    run( apply_argument_parser() )