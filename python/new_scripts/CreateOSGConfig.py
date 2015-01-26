#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, time, re, multiprocessing, glob, logging, shutil
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=logging.DEBUG)
import utils 
import viewer_conf_api

# Script to create the XML configuration file from the OSG data in the DB 

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
    if not opts.output.endswith(".conf.xml"):
        logging.error("The output file must end with .conf.xml")
        return
    
    # Create python postgres connection
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    # Get the root object: the OSG configuration
    rootObject = viewer_conf_api.osgRCconfiguration()
    # set version
    rootObject.set_version("0.2")
    
    # Add all the different XML of the active objects (we add distinct since the boundings will share XMLs) 
    cursor.execute('select distinct xml_path from active_objects_sites')
    for (xmlPath,) in cursor:
        if xmlPath.count(opts.osg) == 0:
            logging.error('Mismatch between given OSG data directory and DB content')
        rootObject.add_objectLibrary(viewer_conf_api.objectLibrary(url=xmlPath.replace(opts.osg,'')))
    
    # Add the object library with the boundings
    rootObject.add_objectLibrary(viewer_conf_api.objectLibrary(url=utils.BOUNDINGS_XML_RELATIVE))
    
    # Add the cameras
    cursor.execute('select camera_name, x, y, z, h, p, r from cameras')
    cameras = viewer_conf_api.cameras()
    for (name, x, y, z, h, p, r) in cursor:
        cameras.add_camera(viewer_conf_api.camera(name=name,x=x,y=y,z=z,h=h,p=p,r=r))
    cursor.execute('SELECT distinct site_id, x, y, z, h, p, r from active_objects_sites_objects where site_id not in (select distinct site_id from cameras where site_id is not null) and object_id = %s order by site_id', [utils.SITE_OBJECT_NUMBER])
    for (siteId,x,y,z,h,p,r) in cursor:
        cameras.add_camera(viewer_conf_api.camera(name=utils.DEFAULT_CAMERA_PREFIX + str(siteId),x=x,y=y,z=z,h=h,p=p,r=r))
    rootObject.set_cameras(cameras)
    # Add the XML content of the preferences
    #cursor.execute('select xml_content from preferences')
    #row  = cursor.fetchone()
    #if row == None:
    #    logging.warn('preferences are not set!. Setting default')
    rootObject.set_preferences(viewer_conf_api.parseString(DEFAULT_PREFENCES))
    #else:
    #    rootObject.set_preferences(viewer_conf_api.parseString(row[0]))
    
    attributes = viewer_conf_api.attributes()  
        
    # Use generic method to fill all properties. We need the name in the XML, the column name in the DB and the table name in the DB
    for property in utils.PROPERTIES_ORDER:
        (cName, tName) = utils.PROPERTIES[property]
        elements = getattr(viewer_conf_api, property + 's')()
        # We need to call the columns and tables with extra "" because they were created from the Access DB
        cursor.execute('SELECT "' + cName + '" from "' + tName + '"')
        for (element,) in cursor:
            getattr(elements, 'add_' + property)(getattr(viewer_conf_api,property)(name=element))
        getattr(attributes, 'set_' + property + 's')(elements)            
    
    rootObject.set_attributes(attributes)
    
    # Add all the static objects, i.e. the OSG from the background
    cursor.execute('select osg_path from static_objects')
    staticObjects = viewer_conf_api.staticObjects()
    for (osgPath,) in cursor:
        if osgPath.count(opts.osg) == 0:
            logging.error('Mismatch between given OSG data directory and DB content')
        staticObjects.add_staticObject(viewer_conf_api.staticObject(url=osgPath.replace(opts.osg,'')))
    
    # Add hardcoded DOME
    staticObjects.add_staticObject(viewer_conf_api.staticObject(url='DOMES/skydome.osg'))
    
    rootObject.set_staticObjects(staticObjects)
    
    # Add the 5 different layers of active objects
    activeObjects = viewer_conf_api.activeObjects()
    # First we add points, meshes and pcitures which are related to the active_objects_sites
    layersData = [('points','sites_pc','pc'),
                  ('photos','sites_pictures','pic'),
                  ('meshes','sites_meshes','mesh')]
    for (layerName,tableName,inType) in layersData:
        layer = viewer_conf_api.layer(name=layerName)
        cursor.execute('select site_id,active_object_site_id,osg_path,x,y,z,xs,ys,zs,h,p,r,cast_shadow from active_objects_sites where active_object_site_id in (select active_object_site_id from ' + tableName + ') order by site_id')
        rows = cursor.fetchall()
        for (siteId,activeObjectId,osgPath,x,y,z,xs,ys,zs,h,p,r,castShadow) in rows:
            fname = os.path.basename(os.path.dirname(osgPath))
            uname = utils.getOSGDescrition(siteId, inType, activeObjectId, fname)
            activeObject = viewer_conf_api.activeObject(prototype=uname, uniqueName=uname)
            setting = viewer_conf_api.setting(x=x,y=y,z=z,xs=xs,ys=ys,zs=zs,h=h,p=p,r=r,castShadow=(1 if castShadow else 0))
            activeObject.set_setting(setting)
            layer.add_activeObject(activeObject)
        activeObjects.add_layer(layer)
        
    # Add the boundings
    layer = viewer_conf_api.layer(name='boundings')
    cursor.execute('select site_id,object_id,name,x,y,z,xs,ys,zs,h,p,r,cast_shadow from active_objects_sites_objects, boundings WHERE active_objects_sites_objects.bounding_id = boundings.bounding_id order BY site_id')
    rows = cursor.fetchall()
    for (siteId,objectNumber,boundingName,x,y,z,xs,ys,zs,h,p,r,castShadow) in rows: 
        uname = utils.getOSGDescrition(siteId, 'obj', objectNumber)
        proto = boundingName
        activeObject = viewer_conf_api.activeObject(prototype=proto, uniqueName=uname)
        setting = viewer_conf_api.setting(x=x,y=y,z=z,xs=xs,ys=ys,zs=zs,h=h,p=p,r=r,castShadow=(1 if castShadow else 0))
        activeObject.set_setting(setting)
        layer.add_activeObject(activeObject)    
    activeObjects.add_layer(layer)
    
    # Add the labels
    layer = viewer_conf_api.layer(name='labels')
    cursor.execute('select name,text,red,green,blue,rotatescreen,outline,font,x,y,z,xs,ys,zs,h,p,r,cast_shadow from active_objects_labels')
    rows = cursor.fetchall()
    for (uname,text,red,green,blue,rotatescreen,outline,font,x,y,z,xs,ys,zs,h,p,r,castShadow) in rows: 
        proto = "labelPrototype"
        activeObject = viewer_conf_api.activeObject(prototype=proto, uniqueName=uname, labelText=text, labelColorRed=red, labelColorGreen=green,
                                                    labelColorBlue=blue, labelRotateScreen=rotatescreen, outline=outline, Font=font)
        setting = viewer_conf_api.setting(x=x,y=y,z=z,xs=xs,ys=ys,zs=zs,h=h,p=p,r=r,castShadow=(1 if castShadow else 0))
        activeObject.set_setting(setting)
        layer.add_activeObject(activeObject)    
    activeObjects.add_layer(layer)
        
    rootObject.set_activeObjects(activeObjects)
    
    # Create the XML
    rootObject.export(open(opts.output,'w'), 0)
    
if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Create the XML configuration file from the OSG data in the DB"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-d','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-o','--osg',default=utils.DEFAULT_OSG_DATA_DIR,help='OSG data directory [default ' + utils.DEFAULT_OSG_DATA_DIR + ']',type='string')
    op.add_option('-f','--output',default='',help='XML file',type='string')
    (opts, args) = op.parse_args()
    main(opts)
