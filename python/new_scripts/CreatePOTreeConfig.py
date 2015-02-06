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
import argparse
import json
import utils
import logging

# CONSTANTS
LOG_FILENAME = 'CreatePOTreeConfig.log'

# Global variables
jsonData ={}

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to generate JSON file for a Point Cloud (PC) visualization from the (ViaAppia) database")
    parser.add_argument('-o','--output',help='Output JSON file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name where the PC data are stored [default ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=True)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=True)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('-l','--location',default='',help='POTree root directory location',type=str, required=False)
    
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

    
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

def create_features_json(cursor, pc_ids, args):
    global jsonData
    
    relative_to_path = args.location
    
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
        sql_statement ='select minx, miny, minz, maxx, maxy, maxz from raw_data_item_pc where raw_data_item_id = %s', [siteId,]        
        cursor.execute(sql_statement)
        if (cursor.rowcount >0):
            (minx, miny, minz, maxx, maxy, maxz) = cursor.fetchone()
        siteFeaturesDict["bbox"] = [minx, miny, minz, maxx, maxy, maxz]
        
        # fetch the geometry of the site from the DB
        sql_statement = 'select st_asgeojson(geom::geometry,15,4) from raw_data_item_pc natural join raw_data_item natural join item where raw_data_item_id = %s', [siteId,]
        cursor.execute(sql_statement)  
        if (cursor.rowcount >0):
            data = cursor.fetchone()[0]
            json_data = json.loads(data)
            json_data_crs = json_data['crs'];
            json_data_geometry= dict(json_data)
            json_data_geometry.pop('crs')
        
        
            siteFeaturesDict["geometry"] = json_data_geometry
            siteFeaturesDict["crs"] = json_data_crs
        
        # fetch the properties of the site from the DB 
        sql_statement = 'select abs_path from raw_data_item natural join raw_data_item_pc where (raw_data_item_id = %s',[siteId,]
        cursor.execute(sql_statement)
        if (cursor.rowcount >0):
             abs_path =  cursor.fetchone()[0]
             rel_path = abs_path.replace(relative_to_path,'')
             properties["pointcloud"] = rel_path
        
        sql_statement = 'select description_site, site_context, site_interpretation from tbl1_site natural join raw_data_item where raw_data_item_id = %s', [siteId,]
        cursor.execute(sql_statement)
        if (cursor.rowcount >0):
            (description, context, interpretation) = cursor.fetchone()
            properties["description"] = description
            properties["site_context"] = context
            properties["site_interpretation"] = interpretation
        
        sql_statement = 'select abs_path from raw_data_item natural join raw_data_item_picture where (thumbnail=True) and (raw_data_item_id = %s)', [siteId,]
        cursor.execute(sql_statement)
        if (cursor.rowcount >0):
             abs_path =  cursor.fetchone()[0]
             rel_path = abs_path.replace(relative_to_path,'')
             properties["thumbnail"] = rel_path

        
        siteFeaturesDict["properties"]=properties
        
        # add to the features
        featuresList.append(siteFeaturesDict)
        
    jsonData["features"] = featuresList 


    # coordinate system
#    coord_system = {}
#    coord_system["type"] = "name"
#    crs_props={}
#    crs_props["name"] = "urn:ogc:def:crs:EPSG::" # get this from the geometry above!     
#    coord_system["properties"]=crs_props 
#    jsonData["crs"] = coord_system
     
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
    localtime = utils.getCurrentTimeAsAscii()
    msg = 'CreatePOTreeConfig scipt logging start at %s'% localtime
    print msg
    logging.info(msg)

    #t0 = time.time()          
    t0 = utils.getCurrentTime()
       
    # connect to DB and get a cursor   
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost)
        
    # get all sites for which we have converted Point Clouds (PCs)        
    sql_statement = 'select distinct raw_data_item_id from potree_data_item_pc'        
    pc_ids, num_pc_ids = utils.fetchDataFromDB(cursor, sql_statement)
    
    # generate the generic JSON file parts
    create_fixed_json_fields()
    
    # generate the features in JSON format
    create_features_json(cursor, pc_ids, args)
    
    # close the Db connection
    utils.closeConnectionDB(connection,cursor)    

    # save the data into JSON file
    save2JSON(args)
    
    elapsed_time = utils.getCurrentTime() - t0    
    msg = 'Finished. Total elapsed time: %s s.' %elapsed_time
    print(msg)
    logging.info(msg)

    # end logging
    localtime = utils.getCurrentTimeAsAscii()  
    msg = 'CreatePOTreeConfig script logging end at %s'% localtime
    print(msg)
    logging.info(msg)
    
    return    

if __name__ == '__main__':
    run( apply_argument_parser() )
