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
#LOG_FILENAME = 'UpdateFootprints.log'

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

def clean_temp_table(args):
    
    drop_table_sql = "DROP TABLE IF EXISTS sites_geoms_temp" 
    utils.dbExecute(cursor, drop_table_sql)
    
    msg = 'Removed table sites_geoms_temp (if existed).'
    print msg
    logger.info(msg)
    
def update_geometries(list_ids, new):
    """ function to update/insert the footprint geometries into the item table
        got a given list of IDs. the new flag indicated weather INSERT or UPDATE
        is needed """
    number = 1
    for (sid,) in list_ids:      
        
        msg = "Processing %s site from %s sites in total"% (number, len(list_ids))
        print msg
        logger.debug(msg)
        
        fetch_geom_sql = "SELECT site_id AS item_id, ST_Multi(ST_Transform( ST_Union(geom), %s)) AS geom FROM sites_geoms_temp WHERE site_id = %s GROUP BY site_id"                
        data,num = utils.fetchDataFromDB(cursor, fetch_geom_sql, [utils.SRID, sid], [], False)

        item_id = data[0][0]
        background = False
        geometry = data[0][1]
        
        if new:            
            insert_geom_sql = "INSERT INTO item VALUES (%s,%s,%s)"            
            utils.dbExecute(cursor, insert_geom_sql, [item_id, background, geometry])
            # We also insert for the new item an entry in item_object
            utils.dbExecute(cursor, "INSERT INTO ITEM_OBJECT (item_id, object_number) VALUES (%s,%s)", [item_id, utils.ITEM_OBJECT_NUMBER_ITEM])
        else: 
            update_geom_sql = "UPDATE item SET background=%s,geom=%s WHERE item_id=%s"            
            utils.dbExecute(cursor, update_geom_sql, [background, geometry, item_id])
            
        
        number = number + 1  
        
        
    msg = "The geometries have been updated!"        
    print msg
    logger.debug(msg)    
    
def update_geom_col_type(cursor):
    """ function to update the initial geometries column type """
    num_items = utils.countElementsTable(cursor, 'item')
    msg = "Number of elements in item table: %s" %num_items        
    print msg
    logger.debug(msg)
            
    col_type = utils.typeColumnTable(cursor, 'geom','item')
    msg = "Current geom column type is %s."%col_type
    print msg
    logger.debug(msg)
 
    if (num_items == 0) or (col_type == 'polygon'): 
        # alter the geometry field type
        alter_type_sql = "ALTER TABLE item ALTER COLUMN geom TYPE geometry(MultiPolygon, " + str(utils.SRID) + ") USING geom:: geometry(MultiPolygon, " + str(utils.SRID) + ")"            
        utils.dbExecute(cursor, alter_type_sql)
        
        msg = "Current geom column type is MultiPolygon, " + str(utils.SRID)
        print msg
        logger.debug(msg)

def find_lists(cursor):
       # find the list of IDs which are in the temporary geometries table, but not in item table           
        no_item_well_temp_sql = "SELECT DISTINCT site_id::integer FROM sites_geoms_temp WHERE (site_id NOT IN (SELECT item_id FROM item))"
        no_item_well_temp_ids, num_ids = utils.fetchDataFromDB(cursor, no_item_well_temp_sql)
        
        msg = "The unique item ids not in item table, but in sites_geoms_temp are %s in number"%num_ids
        print msg
        logger.debug(msg)

        # find the list of IDs which are both in the temporary geometries table and the item table   
        both_in_item_and_temp_sql = "SELECT DISTINCT site_id FROM sites_geoms_temp WHERE (site_id IN (SELECT item_id FROM item))"
        both_in_item_and_temp_ids, num_both_ids = utils.fetchDataFromDB(cursor, both_in_item_and_temp_sql)
        
        msg = "The item ids both in item table and n sites_geoms_temp are %s in number"%num_both_ids
        print msg
        logger.debug(msg)

        return  no_item_well_temp_ids, both_in_item_and_temp_ids
#------------------------------------------------------------------------------        
def run(args): 
    
    global logger
    global connection
    global cursor
    
    # start logging
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=utils.DEFAULT_LOG_LEVEL)
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
    success_loading = utils.load_sql_file(cursor, args.input)
        
    if success_loading:
      
        # check if the SITES table is empty, then change the type of the geom field
        update_geom_col_type(cursor)
        
        # find the lists of new IDs and list of overlapping IDs 
        no_item_well_temp_ids,both_in_item_and_temp_ids = find_lists(cursor) 
                
        # insert the object geometries per site for the sites not in item, but in the sites_geoms_temp table
        update_geometries(no_item_well_temp_ids, True)
    
        # update the union of object geometries per site for the sites both in item and sites_geoms_temp table
        update_geometries(both_in_item_and_temp_ids, False)

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
    run(utils.apply_argument_parser(argument_parser()))