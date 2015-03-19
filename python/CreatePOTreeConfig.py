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
import argparse, json, utils, glob, os, time
logger = None

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to generate a JSON file from the ViaAppiaDB for the ViaAppia POtree web-based visualization")
    parser.add_argument('-o','--output',help='Output JSON file [Log of operation is stored in [output].log]',type=str, required=True)
    parser.add_argument('-s','--srid',default=utils.SRID, help='SRID used in POtree visualization [default ' + str(utils.SRID) + ']',type=int , required=False)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB [default ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
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
    query = 'SELECT A.abs_path, B.thumbnail FROM raw_data_item A, raw_data_item_picture B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.item_id = %s'
    queryArgs = [itemId,]
    site_images, num_site_images = utils.fetchDataFromDB(cursor, query,  queryArgs)
    if num_site_images:
        imageAbsPath = None
        # We use the thumbnail if available
        for (absPath, thumbnail) in site_images:
            if thumbnail:
                imageAbsPath = absPath
        # If no thumbnail is available we just use the first image
        if imageAbsPath == None:
            (absPath, thumbnail) = site_images[0] 
            imageAbsPath = absPath
        jsonSite["thumbnail"] = utils.POTREE_DATA_URL_PREFIX + imageAbsPath.replace(utils.POTREE_SERVER_DATA_ROOT,'') + '/' + os.listdir(imageAbsPath)[0]
    else:
        logger.warning('No image found for item %d' % itemId)

def addSiteMetaData(cursor, itemId, dataSite):
    query = 'SELECT description_site, site_context, site_interpretation FROM tbl1_site WHERE site_id = %s'
    queryArgs = [itemId,]
    site_metadatas, num_site_metadatas = utils.fetchDataFromDB(cursor, query,  queryArgs)
    
    if num_site_metadatas:
        (descriptionSite, siteContext, siteInterpretation) = site_metadatas[0]
        if descriptionSite == None:
            query = 'SELECT description_object FROM tbl1_object WHERE site_id = %s ORDER BY object_id'
            queryArgs = [itemId,]
            object_metadatas, num_object_metadatas = utils.fetchDataFromDB(cursor, query,  queryArgs)
            if num_object_metadatas:
                descriptionSite = object_metadatas[0][0]
        dataSite["description_site"] = descriptionSite
        dataSite["site_context"] = siteContext
        dataSite["site_interpretation"] = siteInterpretation
    else:
        logger.warning('No meta-data found for item %d' % itemId)

def addPointCloud(cursor, itemId, dataSite, srid):
    query = 'SELECT C.abs_path, B.minx, B.miny, B.minz, B.maxx, B.maxy, B.maxz FROM raw_data_item A, raw_data_item_pc B, potree_data_item_pc C WHERE A.raw_data_item_id = B.raw_data_item_id AND B.raw_data_item_id = C.raw_data_item_id AND A.item_id = %s AND A.srid = %s'
    queryArgs = [itemId,srid]
    site_pcs, num_site_pcs = utils.fetchDataFromDB(cursor, query,  queryArgs)
    if num_site_pcs:
        (pcAbsPath, pcMinx, pcMiny, pcMinz, pcMaxx, pcMaxy, pcMaxz) = site_pcs[0] # We only use first PC
        dataSite["pointcloud_bbox"] = [pcMinx, pcMiny, pcMinz, pcMaxx, pcMaxy, pcMaxz]
        dataSite["pointcloud"] = utils.POTREE_DATA_URL_PREFIX + pcAbsPath.replace(utils.POTREE_SERVER_DATA_ROOT,'') + "/cloud.js"
    else:
        logger.warning('No potree point cloud found for item %d SRID %d' % (itemId, srid))

def getOSGPosition(cursor, srid, osgLocationSRID, x, y, z, xs, ys, zs, h, p, r):
    osgPosition = {}
    if srid == osgLocationSRID:
        osgPosition['x'] = x
        osgPosition['y'] = y
        osgPosition['z'] = z
        osgPosition['xs'] = xs
        osgPosition['ys'] = ys
        osgPosition['zs'] = zs
        osgPosition['h'] = h
        osgPosition['p'] = p
        osgPosition['r'] = r
    else:
        if osgLocationSRID != None:
            logger.warning('Found SRID %d (instead of %d). Treating it as None SRID' % (osgLocationSRID, srid))
        # We assume the osg location is relative
        # We need to make it absolute by adding the offset of the background with srid as provided
        query = 'SELECT C.offset_x, C.offset_y, C.offset_z from raw_data_item A, raw_data_item_pc B, osg_data_item_pc_background C WHERE A.raw_data_item_id = B.raw_data_item_id AND B.raw_data_item_id = C.raw_data_item_id AND A.srid = %s'
        queryArgs = [srid,]
        backgroundOffsets, num_backgrounds = utils.fetchDataFromDB(cursor, query,  queryArgs)
        (offsetX,offsetY,offsetZ) = (0,0,0)
        if num_backgrounds:
            (offsetX,offsetY,offsetZ) = backgroundOffsets[0]
        osgPosition['x'] = x + offsetX
        osgPosition['y'] = y + offsetY
        osgPosition['z'] = z + offsetZ
        osgPosition['xs'] = xs
        osgPosition['ys'] = ys
        osgPosition['zs'] = zs
        osgPosition['h'] = h
        osgPosition['p'] = p
        osgPosition['r'] = r
    return osgPosition

def addMeshes(cursor, itemId, dataSite, srid):
    query = """
SELECT 
    A.abs_path, B.mtl_abs_path, B.current_mesh, E.srid, 
    E.x, E.y, E.z, E.xs, E.ys, E.zs, E.h, E.p, E.r
FROM 
    raw_data_item A, raw_data_item_mesh B, osg_data_item_mesh C, 
    osg_data_item D, osg_location E 
WHERE 
    A.raw_data_item_id = B.raw_data_item_id AND
    B.raw_data_item_id = C.raw_data_item_id AND
    C.osg_data_item_id = D.osg_data_item_id AND
    D.osg_location_id = E.osg_location_id AND
    A.item_id = %s"""
    queryArgs = [itemId,]

    site_meshes, num_site_meshes = utils.fetchDataFromDB(cursor, query,  queryArgs)
    
    meshData = None
    recMeshesData = []
    
    if num_site_meshes:
        for (absPath, mtlAbsPath, current, meshSrid, x, y, z, xs, ys, zs, h, p ,r) in site_meshes:
            if not current or (current and meshData == None):
                mData = {}
                mData["data_location"] = utils.POTREE_DATA_URL_PREFIX + (glob.glob(absPath + '/*.obj') + glob.glob(absPath + '/*.OBJ'))[0].replace(utils.POTREE_SERVER_DATA_ROOT,'')
                if mtlAbsPath != None:
                    mData["mtl_location"] = utils.POTREE_DATA_URL_PREFIX + mtlAbsPath.replace(utils.POTREE_SERVER_DATA_ROOT,'')
                mData['osg_position'] = getOSGPosition(cursor, srid, meshSrid, x, y, z, xs, ys, zs, h, p, r)
                if current:
                    meshData = mData
                else:
                    mData['id'] = len(recMeshesData) + 1
                    recMeshesData.append(mData)
    else:
        logger.warning('No meshes found for item %d SRID %d' % (itemId, srid))
    
    if meshData != None:
        dataSite["mesh"] = meshData
    dataSite["reconstruction_mesh"] = recMeshesData

def addObjectsMetaData(cursor, itemId, jsonSite, srid):
    query = 'SELECT object_id, in_situ, ancient, condition, description_object, object_type, object_interpretation, period, date_specific, description_restorations FROM tbl1_object WHERE site_id = %s'
    queryArgs = [itemId,]
    
    site_objects, num_site_objects = utils.fetchDataFromDB(cursor, query,  queryArgs)
    
    objectsData = []
    
    for (object_id, in_situ, ancient, condition, description_object, object_type, object_interpretation, period, date_specific, description_restorations) in site_objects:
        objectData = {}
        objectData['object_id'] = object_id
        objectData['in_situ'] = in_situ
        objectData['ancient'] = ancient
        objectData['condition'] = condition
        objectData['description_object'] = description_object
        objectData['object_type'] = object_type
        objectData['object_interpretation'] = object_interpretation
        objectData['period'] = period
        objectData['date_specific'] = date_specific
        objectData['description_restorations'] = description_restorations
        # Object materials
        objectsMaterialData= []
        query = "SELECT material_type, material_subtype, material_technique FROM tbl2_object_material  WHERE site_id = %s AND object_id = %s"
        queryArgs = [itemId,object_id]
        object_materials, num_object_materials = utils.fetchDataFromDB(cursor, query,  queryArgs)
        for (material_type, material_subtype, material_technique) in object_materials:
            objectMaterialData = {}
            objectMaterialData["id"] = len(objectsMaterialData) + 1
            objectMaterialData["material_type"] = material_type
            objectMaterialData["material_subtype"] = material_subtype
            objectMaterialData["material_technique"] = material_technique
            objectsMaterialData.append(objectMaterialData)
        objectData["object_material"] = objectsMaterialData
        # Object location
        query = "SELECT B.srid, B.x, B.y, B.z, B.xs, B.ys, B.zs, B.h, B.p, B.r FROM osg_item_object A, osg_location B WHERE A.item_id = %s AND A.object_number = %s"
        queryArgs = [itemId,object_id]
        object_locations, num_object_locations = utils.fetchDataFromDB(cursor, query,  queryArgs)
        if num_object_locations:
            (locationSrid, x, y, z, xs, ys, zs, h, p ,r) = object_locations[0]
            objectData['osg_position'] = getOSGPosition(cursor, srid, locationSrid, x, y, z, xs, ys, zs, h, p, r)
            
        objectsData.append(objectData)
    jsonSite["objects"] = objectsData
    
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
    logname = os.path.basename(args.output).split('.')[0] + '.log'
    logger = utils.start_logging(filename=logname, level=args.log)

    # start logging    
    localtime = utils.getCurrentTimeAsAscii()
    msg = __file__ + ' script logging start at %s'% localtime
    print msg
    logger.info(msg)
    t0 = time.time()
       
    # connect to DB and get a cursor   
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost)
        
    # get all items         
    query = 'SELECT item_id, ST_ASGEOJSON(geom), min_z, max_z FROM item WHERE NOT background ORDER BY item_id'
    sites, num_sites = utils.fetchDataFromDB(cursor, query)
    
    data = []
    
    for (itemId, itemGeom, minz, maxz) in sites:
        # Generate the JSON data for this item
        dataSite = {}
        dataSite["id"] = itemId
        if itemGeom != None:
            dataSite["footprint"] = json.loads(itemGeom)['coordinates']
            dataSite["footprint_altitude"] = [minz,maxz]
        
        addThumbnail(cursor, itemId, dataSite)
        addSiteMetaData(cursor, itemId, dataSite)
        addPointCloud(cursor, itemId, dataSite, args.srid)
        addMeshes(cursor, itemId, dataSite, args.srid)
        addObjectsMetaData(cursor, itemId, dataSite, args.srid)
        
        data.append(dataSite)
        
    # close the Db connection
    utils.closeConnectionDB(connection, cursor)    

    # save the data into JSON file
    save2JSON(args.output, data)
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logger.info(msg)

if __name__ == '__main__':
    
    utils.checkSuperUser()
    run( apply_argument_parser() )
