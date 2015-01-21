#!/usr/bin/env python
################################################################################
# Description:      Script to gnerate the JSON file for visualizing the site 
#                   PointClouds in the format outputed by the POTRee converter
# Author:           Elena Ranguelova, NLeSc, E.Ranguelova@nlesc.nl                                       
# Creation date:    21.01.2015      
# Modification date:
# Modifications:   
# Notes:            Based on createjson.py from the Patty FFWD, October 2014
################################################################################
import os, argparse, time
import json
import psycopg2 as pcpg2
import utils 
import logging

# CONSTANTS
DEFAULT_DB = 'vadb' # this should be overrridden eventually by what is the the utils.py
LOG_FILENAME = 'CreatePOTreeConfig.log'

# Global variables
jsonData ={}
connection= None

username = os.popen('whoami').read().replace('\n','')

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to generate JSON file for a Point Cloud (PC) visualization from the (ViaAppia) database")
    parser.add_argument('-o','--output',help='Output JSON file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=DEFAULT_DB,help='PostgreSQL DB name where the PC data are stored [default ' + DEFAULT_DB + ']',type=str , required=True)
    parser.add_argument('-u','--dbuser',default=username,help='DB user [default ' + username + ']',type=str, required=True)
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

def connect_to_db(args):
    global connection 
    
    # Start DB connection
    try: 
        connection = pcpg2.connect(utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, False))
        
    except Exception, E:
        err_msg = 'Cannot connect to %s DB.'% args.dbname
        print(err_msg)
        logging.error((err_msg, "; %s: %s" % (E.__class__.__name__, E)))
        raise
        
    msg = 'Succesful connection to %s DB.'%args.dbname
    print msg
    logging.debug(msg)
    
    # if the connection succeeded get a cursor    
    cursor = connection.cursor()
        
    return cursor
    
def close_db_connection(cursor):
    global connection 
    
    cursor.close()
    connection.close()    
    
    msg = 'Connection to the DB is closed.'
    print msg
    logging.debug(msg)
    
    return

def fetch_data_from_db(cursor):
    
    # get all sites for which there are converted PCes with the POTree converter
    sql_statement = 'select distinct site_pc_id from potree_site_pc'
    
    try:
        cursor.execute(sql_statement)
    except Exception, E:
        err_msg = "Cannot execute the SQL query: %s" % sql_statement
        print(err_msg)
        logging.error((err_msg, "; %s: %s" % (E.__class__.__name__, E)))
        raise
    
    pc_ids = cursor.fetchall()
    
    num_sites = cursor.rowcount
    msg = 'Retrived information for %s sites.'%num_sites
    print msg
    logging.debug(msg)

    if num_sites > 0:    
        print 'Sites: '
        for pcid in pc_ids:
            print pcid                
    return pc_ids

def create_fixed_json_fields():
    global jsonData
    
    # type of the JSON file
    jsonData["type"] = "FeatureCollection"
    jsonData["crs"] = {} 
    
#    # coordinate system
#    coord_system = {}
#    coord_system["type"] = "name"
#    crs_props={}
#    # crs_props["name"] = "urn:ogc:def:crs:EPSG::32633" - original line
#    #crs_props["name"] = "urn:ogc:def:crs:EPSG::" - get this from the geometry!
#    coord_system["properties"]=crs_props 
#    jsonData["crs"] = coord_system
    
    msg = 'Created fixed JSON file parts.'
    print(msg)
    logging.debug(msg)
#    pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
#    print(pretty_json)
#    logging.debug(pretty_json)

def create_features_json(cursor, pc_ids):
    global jsonData
    
       # features per sites
    featuresList = []
    
    for pc in pc_ids:
        
        # initialize the features data structure        
        siteFeaturesDict = {}
        
        siteFeaturesDict["type"] = "Feature"
        siteFeaturesDict["geometry"]={}
        (siteId,) = pc       
        siteFeaturesDict["id"] = siteId
        siteFeaturesDict["properties"]={}
        siteFeaturesDict["bbox"]=""
        
        properties={}
        properties["pointcloud"]=""
        properties["description"]=""
        properties["thumbnail"]=""
        properties["site_context"]=""
        properties["site_interpretation"]=""
        properties["condition"]=""
        
        # fetch the BBox from the DB
        cursor.execute('select minx, miny, minz, maxx, maxy, maxz from site_pc where site_pc_id = %s', [siteId,])
        if (cursor.rowcount >0):
            (minx, miny, minz, maxx, maxy, maxz) = cursor.fetchone()
        siteFeaturesDict["bbox"] = [minx, miny, minz, maxx, maxy, maxz]
        
        # fetch the geometry of the site from the DB
        cursor.execute('select st_asgeojson(geom::geometry) from site_pc where site_pc_id = %s', [siteId,])  
        if (cursor.rowcount >0):
            geometry = cursor.fetchone()[0]
            siteFeaturesDict["geometry"] = json.loads(geometry)
        
            #crs_props["name"] = "urn:ogc:def:crs:EPSG::" - get this from the geometry!
        
#        # fetch the properties of the site from the DB 
#        cursor.execute('select js_path from pc_converted_file, site_pc where (pc_converted_file.pc_id= site_pc.pc_id) and (site_id = %s)', [siteId,])
#        if (cursor.rowcount >0):
#            properties["pointcloud"] = cursor.fetchone()[0]
#        
        cursor.execute('select description_site, site_context, site_interpretation from tbl1_site where site_id = %s', [siteId,])
        if (cursor.rowcount >0):
            (description, context, interpretation) = cursor.fetchone()
            properties["description"] = description
            properties["site_context"] = context
            properties["site_interpretation"] = interpretation
        
#        
#        cursor.execute('select pic_path from site_picture where site_id = %s and thumbnail=True', [siteId,])
#        if (cursor.rowcount >0):
#            properties["thumbnail"]=cursor.fetchone()[0]
        
        siteFeaturesDict["properties"]=properties
        
        # add to the features
        featuresList.append(siteFeaturesDict)
        
    jsonData["features"] = featuresList 


    # coordinate system
    coord_system = {}
    coord_system["type"] = "name"
    crs_props={}
    crs_props["name"] = "urn:ogc:def:crs:EPSG::" # get this from the geometry above!     
    coord_system["properties"]=crs_props 
    jsonData["crs"] = coord_system
     
    msg = 'Created the features in JSON format.'
    print(msg)
    logging.debug(msg)
    pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
    print(pretty_json)
    logging.debug(pretty_json)    
    
def save2JSON(args):
    global jsonData
    
    with open(args.output, 'w') as outfile:
        pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
        outfile.write(pretty_json)
    msg = 'JSON data written to the output file.'
    print(msg)
    logging.debug(msg)
#------------------------------------------------------------------------------        
def run(args):    
    
    # start logging    
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)  
    localtime = time.asctime( time.localtime(time.time()) )   
    msg = 'CreatePOTreeConfig scipt logging start at %s'% localtime
    print msg
    logging.info(msg)

    t0 = time.time()          
       
    # connect to DB and get a cursor   
    cursor = connect_to_db(args)
        
    # get all sites for which we have converted Point Clouds (PCs)        
    pc_ids = fetch_data_from_db(cursor)
    
    # generate the generic JSON file parts
    create_fixed_json_fields()
    
    # generate the features in JSON format
    create_features_json(cursor, pc_ids)
    
    # close the Db connection
    close_db_connection(cursor)    

    # save the data into JSON file
    save2JSON(args)
    
    elapsed_time = time.time() - t0    
    msg = 'Finished. Total elapsed time: %s s.' %elapsed_time
    print(msg)
    logging.info(msg)

    # end logging
    localtime = time.asctime( time.localtime(time.time()) )   
    msg = 'CreatePOTreeConfig script logging end at %s'% localtime
    print(msg)
    logging.info(msg)
    
    return    

if __name__ == '__main__':
    run( apply_argument_parser() )
