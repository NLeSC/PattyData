#!/usr/bin/env python
##############################################################################
# Description:      Script to create the XML configuration file from the OSG
#                   data in the DB
# Authors:          Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
# Created:          26.01.2015
# Last modified:    28.01.2015
# Changes:
# Notes:
##############################################################################

import os
import time
import glob
import utils
import argparse
import viewer_conf_api

logger = None

DEFAULT_PREFENCES = """
<preferences>
    <objectRotationSnap degrees="15.000" pixels="5.000" />
    <cameraParameters>
        <screen touch="0" />
        <mouse accel="1.234" friction="0.000" steerFriction="0.100" />
        <softBrake friction="0.900" />
        <keysLeftRight accel="1.234" friction="0.000" />
        <keysForwardBackward accel="1.234" friction="0.000" />
        <keysVerticalUpDown accel="1.234" friction="0.000" />
        <flySmoothlyToCameras on="0" />
        <walkMode type="off" height="1.750" />
    </cameraParameters>
    <slaveViewClearPitch on="0" />
    <clip near_2exp="-13" far_2exp="96" />
    <simulation maxCars="0" personDensity="0.000" roads="default.roadnetwork" rooms="default.roomnetwork" />
    <LODscale value="0.597" />
    <light diffuse="0.992" ambient="0.270" sun_altitude="57.000" sun_azimuth="111.000" position_latitude="41.900" position_longitude="12.500" shadowIntensity="0.000" ssaoIntensity="0.000" />
    <shadow nearplane="23" farplane="36" mapcount="4" mapsize="9" polyoffsetfactor="3" polyoffsetunits="727" update_shadowmap="1" />
    <backFaceCulling on="1" />
</preferences>"""


def run(opts):
    global logger
    # Define logger and start logging
    #logname = os.path.basename(opts.output) + '.log'
    logname = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logger = utils.start_logging(filename=logname, level=opts.log)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logger.info(msg)

    if not opts.output.endswith(".conf.xml"):
        logger.error('The output file must end with .conf.xml')
        raise IOError('The output file must end with .conf.xml')

    # Create python postgres connection
    global cursor
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)
    
    # Check that provided background is in DB
    query = """
SELECT OSG_DATA_ITEM_PC_BACKGROUND.abs_path,srid 
FROM OSG_DATA_ITEM_PC_BACKGROUND JOIN RAW_DATA_ITEM USING (raw_data_item_id)"""
    rows, num_rows = utils.fetchDataFromDB(cursor, query)
    backGroundAbsPath = None
    backgroundSRID = None
    for (bgAbsPath,bgSRID) in rows:
        if opts.background == os.path.basename(bgAbsPath):
            backGroundAbsPath = bgAbsPath
            backgroundSRID = bgSRID
    if backGroundAbsPath == None:
        errorMsg = 'Background ' + opts.background + ' is not found'
        logger.error(errorMsg)
        raise Exception(errorMsg)
    
    # Get the root object: the OSG configuration
    rootObject = viewer_conf_api.osgRCconfiguration()
    # set version
    rootObject.set_version("0.2")

    # Add all the different XML of the active objects
    # (we add distinct since the boundings will share XMLs)
    query = """
SELECT DISTINCT xml_abs_path 
FROM OSG_DATA_ITEM ORDER BY xml_abs_path"""
    rows, num_rows = utils.fetchDataFromDB(cursor, query)
    for (xmlPath,) in rows:
        if xmlPath.count(opts.osg) == 0:
            logger.error('Mismatch between given OSG data directory ' +
                         'and DB content')
        rootObject.add_objectLibrary(viewer_conf_api.objectLibrary
                                     (url=os.path.relpath(xmlPath, opts.osg)))

    # Add the object library with the boundings
    rootObject.add_objectLibrary(viewer_conf_api.objectLibrary
                                 (url=utils.BOUNDINGS_XML_RELATIVE))

    # Add the cameras that are in the DB
    cameras = viewer_conf_api.cameras()
    query = """
SELECT osg_camera_name, srid, x, y, z, h, p, r 
FROM OSG_CAMERA JOIN OSG_LOCATION USING (osg_location_id)"""
    rows, num_rows = utils.fetchDataFromDB(cursor, query)
    for (name, srid, x, y, z, h, p, r) in rows:
        if (srid is not None) and (srid == bgSRID):
            x, y, z = getOSGPosition(x, y, z, srid)
        else:
            x, y, z = getOSGPosition(x, y, z)
        cameras.add_camera(viewer_conf_api.camera
                           (name=name, x=x, y=y, z=z, h=h, p=p, r=r))
    # Add Default cameras for the items that have no camera in the DB
    query = """
SELECT 
    item_id, ST_SRID(geom), st_x(st_centroid(geom)), st_y(st_centroid(geom)), min_z + ((max_z - min_z) / 2) 
FROM ITEM WHERE NOT background AND geom IS NOT null AND item_id NOT IN (
    SELECT DISTINCT item_id FROM OSG_ITEM_CAMERA
) ORDER BY item_id"""
    rows, numitems = utils.fetchDataFromDB(cursor, query)
    for (itemId, srid, x, y, z) in rows:
        # only call getOSGPosition if [x,y,z] are not None
        # should item_id = -1 be added? 
        if all(position is not None for position in [x,y,z]) and itemId>0:
            if (srid is not None) and (srid == bgSRID):
                x, y, z = getOSGPosition(x, y, z, srid)
            else:
                x, y, z = getOSGPosition(x, y, z)
            cameras.add_camera(viewer_conf_api.camera
                               (name=utils.DEFAULT_CAMERA_PREFIX + str(itemId),
                                x=x, y=y, z=z))
    rootObject.set_cameras(cameras)
    
    # Add the XML content of the preferences
    rootObject.set_preferences(viewer_conf_api.parseString(DEFAULT_PREFENCES))
    
    attributes = viewer_conf_api.attributes()
    # Use generic method to fill all properties.
    # We need the name in the XML, the column name in the DB and
    # the table name in the DB
    for property in utils.ATTRIBUTES_ORDER:
        (cName, tName) = utils.ATTRIBUTES[property]
        elements = getattr(viewer_conf_api, property + 's')()
        # We need to call the columns and tables with extra "" because
        # they were created from the Access DB
#        utils.dbExecute(cursor, 'SELECT "' + cName + '" FROM "' + tName + '"')
        utils.dbExecute(cursor, 'SELECT ' + cName + ' FROM ' + tName)

        for (element,) in cursor:
            getattr(elements, 'add_' + property)(getattr(
                viewer_conf_api, property)(name=element))
        getattr(attributes, 'set_' + property + 's')(elements)
    rootObject.set_attributes(attributes)
    # Add all the static objects, i.e. the OSG from the background

    # Add the static object for the background
    staticObjects = viewer_conf_api.staticObjects()
    staticObjects.add_staticObject(viewer_conf_api.staticObject
                                           (url=os.path.relpath(
                                           glob.glob(backGroundAbsPath + '/' + utils.OSG_DATA_PREFIX + '.osgb')[0],
                                           opts.osg)))
    # Add hardcode DOME
    staticObjects.add_staticObject(viewer_conf_api.staticObject
                                   (url=utils.DOMES_OSG_RELATIVE))
    rootObject.set_staticObjects(staticObjects)

    # Add the 5 different layers of active objects
    activeObjects = viewer_conf_api.activeObjects()
    # First we add points, meshes and pcitures which are related to
    # the active_objects_sites
    layersData = [('points', 'OSG_DATA_ITEM_PC_SITE', utils.AO_TYPE_PC),
                  ('photos', 'OSG_DATA_ITEM_PICTURE', utils.AO_TYPE_PIC),
                  ('meshes', 'OSG_DATA_ITEM_MESH', utils.AO_TYPE_MESH)]
    
    for (layerName, tableName, inType) in layersData:
        layer = viewer_conf_api.layer(name=layerName)
        
        query = """
SELECT item_id, raw_data_item_id, OSG_LOCATION.srid, x, y, z, xs, ys, zs, h, p, r, cast_shadow 
FROM """ + tableName + """ JOIN OSG_DATA_ITEM USING (osg_data_item_id) 
                           JOIN OSG_LOCATION  USING (osg_location_id) 
                           JOIN RAW_DATA_ITEM USING (raw_data_item_id) 
ORDER BY item_id"""
        rows, numitems = utils.fetchDataFromDB(cursor, query)
        for (itemId, rawDataItemId, srid, x, y, z, xs, ys, zs, h, p, r, castShadow) in rows:
            # only call getOSGPosition if [x,y,z] are not None            
            if all(position is not None for position in [x,y,z]):
                if (srid is not None) and (srid == bgSRID):
                    x, y, z  = getOSGPosition(x, y, z, srid)
                else:
                    x, y, z = getOSGPosition(x, y, z)
            uniqueName = utils.codeOSGActiveObjectUniqueName(cursor, inType, rawDataItemId)
            activeObject = viewer_conf_api.activeObject(prototype=uniqueName,
                                                        uniqueName=uniqueName)
            setting = viewer_conf_api.setting(
                x=x, y=y, z=z, xs=xs, ys=ys, zs=zs, h=h, p=p, r=r,
                castShadow=(1 if castShadow else 0))
            activeObject.set_setting(setting)
            layer.add_activeObject(activeObject)
        activeObjects.add_layer(layer)

    # Add the boundings
    layer = viewer_conf_api.layer(name='boundings')
    # We first add the boundings that are currently in the DB
    query = """
SELECT item_id, object_number, x, y, z, xs, ys, zs, h, p, r, OSG_LOCATION.cast_shadow, srid 
FROM OSG_ITEM_OBJECT JOIN OSG_LOCATION USING (osg_location_id) 
ORDER BY item_id,object_number"""
    osgItemObjects, numOsgItemObjects = utils.fetchDataFromDB(cursor, query)
    # osgItemObjects is (itemId, objectNumber, x, y, z, xs, ys, zs, h, p, r, castShadow, srid)
    # Now we add Default OSG data items for the objects that are not in OSG_ITEM_OBJECT table
    query = """
SELECT item_id,object_number 
FROM item_object 
WHERE (item_id,object_number) NOT IN (SELECT item_id,object_number FROM OSG_ITEM_OBJECT)
ORDER BY item_id,object_number"""
    objects, num_objects = utils.fetchDataFromDB(cursor, query)
    for (itemId, objectNumber) in objects:
        srid = None
        (x,y,z) = (0,0,0)
        (xs,ys,zs) = (1,1,1)
        query = """
SELECT ST_SRID(geom), st_x(st_centroid(geom)), st_y(st_centroid(geom)), min_z + ((max_z - min_z) / 2), 
       st_xmax(geom)-st_xmin(geom) as dx, st_ymax(geom)-st_ymin(geom) as dy, (max_z - min_z) as dz 
FROM ITEM 
WHERE item_id = %s and geom is not %s"""
        queryArgs = [itemId, None]
        footprints, num_footprints = utils.fetchDataFromDB(cursor, query, queryArgs)
        if num_footprints:
            (srid, x, y, z, xs, ys, zs) = footprints[0]
            if xs == 0: xs = 1
            if ys == 0: ys = 1
            if zs == 0: zs = 1
        osgItemObjects.append([itemId, objectNumber, x, y, z, xs, ys, zs, 0, 0, 0, False, srid])
    # Now let's add them to the XML
    for (itemId, objectNumber, x, y, z, xs, ys, zs, h, p, r, castShadow, srid) in osgItemObjects:
        # only call getOSGPosition if [x,y,z] are not None
        if all(position is not None for position in [x,y,z]) and itemId>0:        
            if (srid is not None) and (srid == bgSRID):
                x, y, z  = getOSGPosition(x, y, z, srid)
            else:
                x, y, z = getOSGPosition(x, y, z)                
            uniqueName = utils.codeOSGActiveObjectUniqueName(cursor, utils.AO_TYPE_OBJ, itemId = itemId, objectId = objectNumber)
            proto = "Bounding Box"
            activeObject = viewer_conf_api.activeObject(prototype=proto,
                                                        uniqueName=uniqueName)
            setting = viewer_conf_api.setting(
                x=x, y=y, z=z, xs=xs, ys=ys, zs=zs, h=h, p=p, r=r,
            castShadow=(1 if castShadow else 0))
            activeObject.set_setting(setting)
            layer.add_activeObject(activeObject)
    activeObjects.add_layer(layer)

    # Add the labels
    layer = viewer_conf_api.layer(name='labels')
    utils.dbExecute(cursor, 'SELECT osg_label_name, text, red, green, blue, ' +
                    'rotate_screen, outline, font, srid, x, y, z, xs, ys, zs, h, ' +
                    'p, r, cast_shadow FROM OSG_LABEL INNER JOIN ' +
                    'OSG_LOCATION ON OSG_LABEL.osg_location_id=' +
                    'OSG_LOCATION.osg_location_id')
    rows = cursor.fetchall()
    for (name, text, red, green, blue, rotatescreen, outline, font, srid, x, y, z, xs, ys, zs, h, p, r, castShadow) in rows:
        proto = "labelPrototype"
        uniqueName = utils.codeOSGActiveObjectUniqueName(cursor, utils.AO_TYPE_LAB, labelName = name)
        if (srid is not None) and (srid == bgSRID):
            x, y, z = getOSGPosition(x, y, z, srid)
        else:
            x, y, z = getOSGPosition(x, y, z)
        activeObject = viewer_conf_api.activeObject(
            prototype=proto, uniqueName=uniqueName, labelText=text,
            labelColorRed=red, labelColorGreen=green, labelColorBlue=blue,
            labelRotateScreen=rotatescreen, outline=outline, Font=font)
        setting = viewer_conf_api.setting(
            x=x, y=y, z=z, xs=xs, ys=ys, zs=zs, h=h, p=p, r=r,
            castShadow=(1 if castShadow else 0))
        activeObject.set_setting(setting)
        layer.add_activeObject(activeObject)
    activeObjects.add_layer(layer)

    rootObject.set_activeObjects(activeObjects)

    # Create the XML
    rootObject.export(open(opts.output, 'w'), 0)
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logger.info(msg)

def getOSGPosition(x, y, z, ItemSRID=None):
    if (ItemSRID is not None):
        backgroundOffsets, num_backgrounds = utils.fetchDataFromDB(
            cursor, 'SELECT offset_x, offset_y, offset_z, srid FROM ' +
            'OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM ON ' +
            'OSG_DATA_ITEM_PC_BACKGROUND.raw_data_item_id=' +
            'RAW_DATA_ITEM.raw_data_item_id')
        background = [BACK for BACK in backgroundOffsets if 
                      BACK[3] == ItemSRID]
        if len(background) == 0:
            logger.warning('No background with the same SRID %s is found'
                % (ItemSRID))
        #if len(background) > 1:
        #    logger.warning('Multiple backgrounds with the same SRID %s found'
        #        % (ItemSRID))
        else:
            # found the associated background in the database
            offset_x, offset_y, offset_z, srid = background[0]
    else:
        offset_x, offset_y, offset_z = 0, 0, 0
    # convert item position to relative to associated background
    x_out = x - offset_x
    y_out = y - offset_y
    z_out = z - offset_z
    return x_out, y_out, z_out

def argument_parser():
    """ Define the arguments and return the parser object"""
    description = 'Create XML configuration file from OSG data in the DB'
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-d', '--dbname', default=utils.DEFAULT_DB,
                        help='Postgres DB name [default ' +
                        utils.DEFAULT_DB + ']', action='store')
    parser.add_argument('-u', '--dbuser', default=utils.USERNAME,
                        help='DB user [default ' + utils.USERNAME +
                        ']', action='store')
    parser.add_argument('-p', '--dbpass', help='DB pass', action='store')
    parser.add_argument('-t', '--dbhost', help='DB host', action='store')
    parser.add_argument('-r', '--dbport', help='DB port', action='store')
    parser.add_argument('-g', '--osg', default=utils.DEFAULT_OSG_DATA_DIR,
                        help='OSG data directory [default ' +
                        utils.DEFAULT_OSG_DATA_DIR + ']', action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)
    parser.add_argument('-b', '--background', help='Background', 
                        default=utils.DEFAULT_BACKGROUND, action='store')
    # required input
    parser.add_argument('-o', '--output', help='XML file', action='store',
                        required=True)

    return parser

if __name__ == "__main__":
    run(utils.apply_argument_parser(argument_parser()))
