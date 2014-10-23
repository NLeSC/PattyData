#!/usr/bin/env python
################################################################################
#   Created by Oscar Martinez, Elena Ranguelova and Milena Ivanova            #
#   www.nlesc.nl                                                               #
################################################################################
import os, argparse, time
import json
import psycopg2 as pcpg2
import utils 

# CONSTANTS
DEFAULT_DB = 'vadb'

# Global variables
connection = None
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
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=True)
    
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

def run(args):    
    t0 = time.time()          
       
    # Global variables declaration
    global connection
    
    # Start DB connection
    connection = pcpg2.connect(utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, False))
    cursor = connection.cursor()
    
    # get all sites for which we have converted Point Clouds (PCs)
    cursor.execute('select site_pc.site_id,pc_converted_file.pc_converted_file_id from pc, pc_converted_file, site_pc where (pc.pc_id = pc_converted_file.pc_id) and (pc.pc_id = site_pc.pc_id)')
    
    pc_ids = cursor.fetchall()
    
        
    jsonData = {}
    # type of the JSON file
    jsonData["type"] = "FeatureCollection"
    jsonData["crs"] = {} 
    
    # coordinate system
    coord_system = {}
    coord_system["type"] = "name"
    crs_props={}
    crs_props["name"] = "urn:ogc:def:crs:EPSG::32633"
    coord_system["properties"]=crs_props 
    jsonData["crs"] = coord_system
    
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
        cursor.execute('select minx, miny, minz, maxx, maxy, maxz from pc, site_pc where pc.pc_id = site_pc.pc_id and site_id = %s', [siteId,])
        if (cursor.rowcount >0):
            (minx, miny, minz, maxx, maxy, maxz) = cursor.fetchone()
        siteFeaturesDict["bbox"] = [minx, miny, minz, maxx, maxy, maxz]
        
        # fetch the geometry of the site from the DB
        cursor.execute('select st_asgeojson(geom::geometry) from site where site_id = %s', [siteId,])  
        if (cursor.rowcount >0):
            geometry = cursor.fetchone()[0]
            siteFeaturesDict["geometry"] = json.loads(geometry)
        # fetch the properties of the site from the DB 
        cursor.execute('select js_path from pc_converted_file, site_pc where (pc_converted_file.pc_id= site_pc.pc_id) and (site_id = %s)', [siteId,])
        if (cursor.rowcount >0):
            properties["pointcloud"] = cursor.fetchone()[0]
        
        cursor.execute('select description_site, site_context, site_interpretation from tbl1_site where site_id = %s', [siteId,])
        if (cursor.rowcount >0):
            (description, context, interpretation) = cursor.fetchone()
            properties["description"] = description
            properties["site_context"] = context
            properties["site_interpretation"] = interpretation
        
        
        cursor.execute('select pic_path from site_picture where site_id = %s and thumbnail=True', [siteId,])
        if (cursor.rowcount >0):
            properties["thumbnail"]=cursor.fetchone()[0]
        
        siteFeaturesDict["properties"]=properties
        
        # add to the features
        featuresList.append(siteFeaturesDict)
        
    jsonData["features"] = featuresList      
   
    
    cursor.close()
    connection.close()
    
    # save the data into JSON file
    with open(args.output, 'w') as outfile:
        pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
        outfile.write(pretty_json)
    
    print 'Finished!. Total time ', time.time() - t0



if __name__ == '__main__':
    run( apply_argument_parser() )
