#!/usr/bin/env python
################################################################################
# Description:      Script to gnerate the JSON file for visualizing the site 
#                   PointClouds in the format outputed by the POTRee converter
# Author:           Elena Ranguelova, NLeSc, E.Ranguelova@nlesc.nl    
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl                                   
# Creation date:    21.01.2015      
# Modification date: 23.02.2015
# Modifications:   
# Notes:            Based on createjson.py from the Patty FFWD, October 2014
################################################################################
import argparse
import json
import utils
logger = None

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to generate a JSON file from the ViaAppiaDB for the ViaAppia POtree web-based visualization")
    parser.add_argument('-o','--output',help='Output JSON file [Log of operation is stored in [output].log]',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB [default ' + utils.DEFAULT_DB + ']',type=str , required=True)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('-l','--location',default=utils.DEFAULT_POTREE_DATA_DIR,help='POTree root directory location [default ' + utils.DEFAULT_POTREE_DATA_DIR + ']',type=str, required=True)
    parser.add_argument('--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

def addThumbnail(cursor, itemId, jsonSite):
    query = 'SELECT A.abs_path, B.thumbnail FROM raw_data_item A, raw_data_item_picture B WHERE A.raw_data_item_id == B.raw_data_item_id AND A.item_id = %s'
    queryArgs = [itemId,]
    images, num_images = utils.fetchDataFromDB(cursor, query,  queryArgs)
    if num_images:
        imageAbsPath = None
        # We use the thumbnail if available
        for (absPath, thumbnail) in images:
            if thumbnail:
                imageAbsPath = absPath
        # If no thumbnail is available we just use the first image
        if imageAbsPath == None:
            (absPath, thumbnail) = images[0] 
            imageAbsPath = absPath
        jsonSite["thumbnail"] = utils.POTREE_DATA_URL_PREFIX + imageAbsPath.replace(utils.POTREE_SERVER_DATA_ROOT,'')

def addSiteMetaData(cursor, itemId, jsonSite):
    query = 'SELECT description_site, site_context, site_interpretation FROM tbl1_site WHERE A.raw_data_item_id == B.raw_data_item_id AND A.item_id = %s'
    queryArgs = [itemId,]
    images, num_images = utils.fetchDataFromDB(cursor, query,  queryArgs)
    
    jsonSite["description_site"] = "Pyramid"
    jsonSite["site_context"] = "Funerary"
    jsonSite["site_interpretation"] = "Funerary tower"
    return


def addPointCloud(cursor, itemId, jsonSite):
    return
def addMeshes(cursor, itemId, jsonSite):
    return
def addObjectsMetaData(cursor, itemId, jsonSite):
    return

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


    msg = 'Created the features in JSON format.'
    print(msg)
    logger.debug(msg)
    pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
    print(pretty_json)
    logger.debug(pretty_json)    
    
def save2JSON(outFileName, jsonData):
    with open(outFileName, 'w') as outfile:
        pretty_json = json.dumps(jsonData, indent=4, separators=(',', ': '))
        outfile.write(pretty_json)
    msg = 'JSON data written to the output file.'
    print(msg)
    logger.debug(msg)
    
#------------------------------------------------------------------------------        
def run(args):    
    global logger
    logger = utils.start_logging(filename=args.output + '.log', level=args.log)

    # start logging    
    localtime = utils.getCurrentTimeAsAscii()
    msg = __file__ + ' script logging start at %s'% localtime
    print msg
    logger.info(msg)
    t0 = utils.getCurrentTime()
       
    # connect to DB and get a cursor   
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost)
        
    # get all items         
    query = 'SELECT item_id, ST_ASGEOJSON(geom) FROM item WHERE NOT background'        
    sites, num_sites = utils.fetchDataFromDB(cursor, query)
    
    jsonData = []
    
    for (itemId, itemGeom) in sites:
        # Generate the JSON data for this item
        jsonSite = {}
        jsonSite["id"] = itemId
        jsonSite["footprint"] = json.loads(itemGeom)['coordinates']
        
        addThumbnail(cursor, itemId, jsonSite)
        addSiteMetaData(cursor, itemId, jsonSite)
        addPointCloud(cursor, itemId, jsonSite)
        addMeshes(cursor, itemId, jsonSite)
        addObjectsMetaData(cursor, itemId, jsonSite)
        
        jsonData.append(jsonSite)
        
    # close the Db connection
    utils.closeConnectionDB(connection, cursor)    

    # save the data into JSON file
    save2JSON(args.output, jsonData)
    
    elapsed_time = utils.getCurrentTime() - t0    
    msg = 'Finished. Total elapsed time: %s s.' %elapsed_time
    print(msg)
    logger.info(msg)

    # end logging
    localtime = utils.getCurrentTimeAsAscii()  
    msg = __file__ + ' script logging end at %s'% localtime
    print(msg)
    logger.info(msg)
    
    return    

if __name__ == '__main__':
    run( apply_argument_parser() )
