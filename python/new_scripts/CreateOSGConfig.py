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
import optparse
import psycopg2
import time
import re
import multiprocessing
import glob
import shutil
import utils
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


def main(opts):
    # Define logger and start logging
    global logger
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script CreateOSGConfig.py')
    logger.info('#######################################')

    if not opts.output.endswith(".conf.xml"):
        logger.error('The output file must end with .conf.xml')
        raise IOError('The output file must end with .conf.xml')

    # Create python postgres connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)

    # Get the root object: the OSG configuration
    rootObject = viewer_conf_api.osgRCconfiguration()
    # set version
    rootObject.set_version("0.2")

    # Add all the different XML of the active objects
    # (we add distinct since the boundings will share XMLs)
    # cursor.execute('SELECT DISTINCT xml_path FROM active_objects_sites')
    cursor.execute('SELECT DISTINCT xml_abs_path FROM OSG_DATA_ITEM')
    for (xmlPath,) in cursor:
        if xmlPath.count(opts.osg) == 0:
            logger.error('Mismatch between given OSG data directory ' +
                         'and DB content')
        rootObject.add_objectLibrary(viewer_conf_api.objectLibrary
                                     (url=xmlPath.replace(opts.osg, '')))

    # Add the object library with the boundings
    rootObject.add_objectLibrary(viewer_conf_api.objectLibrary
                                 (url=utils.BOUNDINGS_XML_RELATIVE))

    # Add the cameras
    # cursor.execute('SELECT camera_name, x, y, z, h, p, r FROM cameras')
    cursor.execute('SELECT osg_camera_name, x, y, z, h, p, r FROM ' +
                   'OSG_CAMERA INNER JOIN OSG_LOCATION ON ' +
                   'OSG_CAMERA.osg_location_id=OSG_LOCATION.osg_location_id')

    cameras = viewer_conf_api.cameras()
    for (name, x, y, z, h, p, r) in cursor:
        cameras.add_camera(viewer_conf_api.camera
                           (name=name, x=x, y=y, z=z, h=h, p=p, r=r))
    # cursor.execute('SELECT DISTINCT site_id, x, y, z, h, p, r FROM ' +
    #                'active_objects_sites_objects WHERE site_id NOT IN ' +
    #                '(SELECT DISTINCT site_id FROM cameras WHERE site_id ' +
    #                'IS NOT null) AND object_id = %s ORDER BY site_id',
    #               [utils.SITE_OBJECT_NUMBER])
    # need OSG_ITEM_CAMERA.item_id instead of OSG_CAMERA.osg_location_id ??
    # ??? object_id -> srid ???
    cursor.execute('SELECT DISTINCT osg_location_id, x, y, z, h, p, r FROM ' +
                   'OSG_LOCATION WHERE osg_location_id NOT IN (SELECT ' +
                   'DISTINCT osg_location_id FROM OSG_CAMERA WHERE ' +
                   'osg_location_id IS NOT null) AND srid = %s ORDER ' +
                   'BY osg_location_id', [utils.SITE_OBJECT_NUMBER])
    for (siteId, x, y, z, h, p, r) in cursor:
        cameras.add_camera(viewer_conf_api.camera
                           (name=utils.DEFAULT_CAMERA_PREFIX + str(siteId),
                            x=x, y=y, z=z, h=h, p=p, r=r))
    rootObject.set_cameras(cameras)
    # Add the XML content of the preferences
    # cursor.execute('select xml_content from preferences')
    # row  = cursor.fetchone()
    # if row == None:
    #    logger.warn('preferences are not set!. Setting default')
    rootObject.set_preferences(viewer_conf_api.parseString(DEFAULT_PREFENCES))
    # else:
    #    rootObject.set_preferences(viewer_conf_api.parseString(row[0]))

    attributes = viewer_conf_api.attributes()

    # Use generic method to fill all properties.
    # We need the name in the XML, the column name in the DB and
    # the table name in the DB
    for property in utils.PROPERTIES_ORDER:
        (cName, tName) = utils.PROPERTIES[property]
        elements = getattr(viewer_conf_api, property + 's')()
        # We need to call the columns and tables with extra "" because
        # they were created from the Access DB
        cursor.execute('SELECT "' + cName + '" FROM "' + tName + '"')
        for (element,) in cursor:
            getattr(elements, 'add_' + property)(getattr(
                viewer_conf_api, property)(name=element))
        getattr(attributes, 'set_' + property + 's')(elements)

    rootObject.set_attributes(attributes)

    # Add all the static objects, i.e. the OSG from the background
    # cursor.execute('SELECT osg_path FROM static_objects')
    cursor.execute('SELECT abs_path FROM OSG_DATA_ITEM_PC_BACKGROUND')
    staticObjects = viewer_conf_api.staticObjects()
    for (osgPath,) in cursor:
        if osgPath.count(opts.osg) == 0:
            logger.error('Mismatch between given OSG ' +
                         'data directory and DB content')
        staticObjects.add_staticObject(viewer_conf_api.staticObject
                                       (url=osgPath.replace(opts.osg, '')))

    # Add hardcoded DOME
    staticObjects.add_staticObject(viewer_conf_api.staticObject
                                   (url='DOMES/skydome.osg'))

    rootObject.set_staticObjects(staticObjects)

    # Add the 5 different layers of active objects
    activeObjects = viewer_conf_api.activeObjects()
    # First we add points, meshes and pcitures which are related to
    # the active_objects_sites
    layersData = [('points', 'sites_pc', 'pc'),
                  ('photos', 'sites_pictures', 'pic'),
                  ('meshes', 'sites_meshes', 'mesh')]
    for (layerName, tableName, inType) in layersData:
        layer = viewer_conf_api.layer(name=layerName)
        # cursor.execute('SELECT site_id, active_object_site_id, osg_path, ' +
        #               'x, y, z, xs, ys, zs, h, p, r, cast_shadow FROM ' +
        #               'active_objects_sites WHERE active_object_site_id ' +
        #               'IN (SELECT active_object_site_id FROM ' +
        #               tableName + ') ORDER BY site_id')
        cursor.execute('SELECT osg_location_id, osg_data_item_id, abs_path, ' +
                       'x, y, z, xs, ys, zs, h, p, r, cast_shadow FROM ' +
                       'OSG_DATA_ITEM INNER JOIN OSG_LOCATION ON ' +
                       'OSG_DATA_ITEM.osg_location_id=' +
                       'OSG_LOCATION.osg_location_id WHERE osg_data_item_id ' +
                       'IN (SELECT osg_data_item_id FROM ' +
                       tableName + ') ORDER BY osg_location_id')

        rows = cursor.fetchall()
        for (siteId, activeObjectId, osgPath, x, y, z, xs, ys, zs, h, p, r,
             castShadow) in rows:
            fname = os.path.basename(os.path.dirname(osgPath))
            uname = utils.getOSGDescrition(siteId, inType, activeObjectId,
                                           fname)
            activeObject = viewer_conf_api.activeObject(prototype=uname,
                                                        uniqueName=uname)
            setting = viewer_conf_api.setting(
                x=x, y=y, z=z, xs=xs, ys=ys, zs=zs, h=h, p=p, r=r,
                castShadow=(1 if castShadow else 0))
            activeObject.set_setting(setting)
            layer.add_activeObject(activeObject)
        activeObjects.add_layer(layer)

    # Add the boundings
    layer = viewer_conf_api.layer(name='boundings')
    # cursor.execute('SELECT site_id, object_id, name, x, y, z, xs, ys, zs, ' +
    #              'h, p, r, cast_shadow FROM active_objects_sites_objects, ' +
    #              'boundings WHERE active_objects_sites_objects.bounding_id' +
    #              ' = boundings.bounding_id ORDER BY site_id')
    # ??? name -> OSG_CAMERA.osg_camera_name ???
    # ??? bounding_id ???
    cursor.execute('SELECT osg_location_id, osg_data_item_id, ' +
                   'osg_camera_name, x, y, z, xs, ys, zs, h, p, r, ' +
                   'cast_shadow FROM OSG_DATA_ITEM INNER JOIN ' +
                   'OSG_LOCATION ON OSG_DATA_ITEM.osg_location_id=' +
                   'OSG_LOCATION.osg_location_id INNER JOIN OSG_LABEL ON ' +
                   'OSG_LOCATION.osg_location_id=OSG_LABEL.osg_location_id ' +
                   'INNER JOIN OSG_CAMERA ON OSG_CAMERA.osg_location=' +
                   'OSG_LOCATION.osg_location_id ' +
                   'WHERE active_objects_sites_objects.bounding_id' +
                   ' = boundings.bounding_id ORDER BY site_id')

    rows = cursor.fetchall()
    for (siteId, objectNumber, boundingName, x, y, z, xs, ys, zs, h, p, r,
         castShadow) in rows:
        uname = utils.getOSGDescrition(siteId, 'obj', objectNumber)
        proto = boundingName
        activeObject = viewer_conf_api.activeObject(prototype=proto,
                                                    uniqueName=uname)
        setting = viewer_conf_api.setting(
            x=x, y=y, z=z, xs=xs, ys=ys, zs=zs, h=h, p=p, r=r,
            castShadow=(1 if castShadow else 0))
        activeObject.set_setting(setting)
        layer.add_activeObject(activeObject)
    activeObjects.add_layer(layer)

    # Add the labels
    layer = viewer_conf_api.layer(name='labels')
    # cursor.execute('SELECT name, text, red, green, blue, rotatescreen, ' +
    #               'outline, font, x, y, z, xs, ys, zs, h, p, r, ' +
    #               'cast_shadow FROM active_objects_labels')
    # ??? name -> OSG_CAMERA.osg_camera_name ???
    cursor.execute('SELECT osg_camera_name, text, red, green, blue, ' +
                   'rotate_screen, outline, font, x, y, z, xs, ys, zs, h, ' +
                   'p, r, cast_shadow FROM OSG_LABEL INNER JOIN ' +
                   'OSG_LOCATION ON OSG_LABEL.osg_location_id=' +
                   'OSG_LOCATION.osg_location_id INNER JOIN OSG_CAMERA ON ' +
                   'OSG_CAMERA.osg_location_id=OSG_LOCATION.osg_location_id')
    rows = cursor.fetchall()
    for (uname, text, red, green, blue, rotatescreen, outline, font, x, y, z,
         xs, ys, zs, h, p, r, castShadow) in rows:
        proto = "labelPrototype"
        activeObject = viewer_conf_api.activeObject(
            prototype=proto, uniqueName=uname, labelText=text,
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


if __name__ == "__main__":
    # define argument menu
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
    parser.add_argument('-o', '--osg', default=utils.DEFAULT_OSG_DATA_DIR,
                        help='OSG data directory [default ' +
                        utils.DEFAULT_OSG_DATA_DIR + ']', action='store')
    # required input ?
    parser.add_option('-f', '--output', help='XML file', action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)