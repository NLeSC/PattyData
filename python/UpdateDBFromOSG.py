#!/usr/bin/env python
##############################################################################
# Description:      Script to update database from OSG config XML changes
# Authors:          Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
# Created:          29.01.2015
# Last modified:
# Changes:
# Notes:            Based on updateconfigxml.py from ViaAppia project
##############################################################################

import os, time, argparse, psycopg2, utils, viewer_conf_api
from lxml import etree as ET
from numpy import array as nparray

logger = None
cursor = None
offsetSRID = None

def getOSGLocationId(cursor, ao, aoType, labelName = None, itemId = None, ObjectId = None, rawDataItemId = None):
    ''' Function to check if the object exists in the DB '''
    if aoType == utils.AO_TYPE_OBJ:
        if (itemId == None) or (objectId == None):
            raise Exception ('Item Object operations require not null itemId and objectId')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_ITEM_OBJECT WHERE item_id = %s AND object_number = %s', [itemId, ObjectId])
    elif aoType == utils.AO_TYPE_LAB:
        if labelName == None:
            raise Exception ('Label operations require not null labelName')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_LABEL WHERE osg_label_name = %s', [labelName,])
    else:
        if rawDataItemId == None:
            raise Exception ('Raw data item operations require not null rawDataItemId')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM ((SELECT * FROM OSG_DATA_ITEM_PC_SITE) UNION (SELECT * FROM OSG_DATA_ITEM_PC_SITE) UNION (SELECT * FROM OSG_DATA_ITEM_PC_SITE)) A JOIN OSG_DATA_ITEM USING (osg_data_item_id) WHERE raw_data_item_id = %s', [rawDataItemId, ])
    if num_rows == 0:
        return None
    else:
        return rows[0][0]

def deleteOSG(cursor, ao, aoType, labelName = None, itemId = None, objectId = None, rawDataItemId = None):
    ''' Function to delete a site object '''
    if aoType == utils.AO_TYPE_OBJ:
        if (itemId == None) or (objectId == None):
            raise Exception ('Item Object operations require not null itemId and objectId')
        # extract osg_location_id of the object
        data,rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_ITEM_OBJECT WHERE item_id = %s AND object_number = %s', [itemId, objectId])
        utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_OBJECT WHERE item_id = %s AND object_number = %s', [itemId, objectId])
        # delete from OSG_LOCATION
        utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE osg_location_id = %s', [data[0][0],])

    elif aoType == utils.AO_TYPE_LAB:
        if labelName == None:
            raise Exception ('Label operations require not null labelName')
        # extract osg_location_id of the label
        data, rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_LABEL WHERE osg_label_name = %s', [labelName,])
        # delete from OSG_LABEL
        utils.dbExecute(cursor,'DELETE FROM OSG_LABEL WHERE osg_label_name = %s', [labelName,])
        # delete from OSG_LOCATION
        utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE osg_location_id = %s', [data[0][0],])
    else:
        raise Exception('Not possible to delete object ' + labelName)


def updateOSGLocation(cursor, ao, aoType, labelName = None, itemId = None, objectId = None, rawDataItemId = None):
    s = ao.getchildren()[0]
    names = []
    auxs = []
    values = []
    # add srid
    names.append('srid')
    auxs.append('%s')
    values.append(offsetSRID[0][-1])
    # add location
    for c in ('x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p', 'r'):
        if c in s.keys():
            names.append(c)
            auxs.append('%s')
            values.append(s.get(c))
    # cast_shadow
    if 'castShadow' in s.keys():
        names.append('cast_shadow')
        auxs.append('%s')
        values.append(False if (s.get('castShadow') == '0') else 1)
    try:
        values[values.index('x')] += offsetSRID[0]
        values[values.index('y')] += offsetSRID[1]
        values[values.index('z')] += offsetSRID[2]
    except ValueError:
        logger.error('No location x,y,z found')
    
    # update the position of the object in OSG_LOCATION table
    OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                         'r', 'cast_shadow']
    update_DB_table(names, values, auxs, OSG_LOCATION_list, 'OSG_LOCATION',
                      cursor)
    return 1



def main(opts):
    # Define logger and start logging
    global logger
    logname = os.path.basename(opts.config).split('.')[0] + '.log'
    logger = utils.start_logging(filename=logname, level=opts.log)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logger.info(msg)

    # Parse xml configuration file
    data = ET.parse(opts.config).getroot()

    # Database connection
    global cursor
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)

    # get offset and srid of the background defined in the conf file
    global offsetSRID
    offsetSRID = get_SRID(data, cursor)
    # Process updates
    updateAOS = data.xpath('//*[@status="updated"]')
    # loop over all updates found in the xml config file
    for ao in updateAOS:
        #(aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        #getDetails(ao)
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) = utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType == None:
            logger.warning('Ignoring operation on %s. Could not decode uniqueName' % uniqueName)
        else:
            # check if the object is in the DB
            inDB = getOSGLocationId(cursor, ao, aoType, labelName, itemId, objectId)
            if inDB:
                # update the DB with the information in the xml config file
                updateSetting(cursor, ao, aoType, labelName, itemId, objectId)
            else:
                if aoType==utils.AO_TYPE_OBJ:
                    # It is a bounding that has been moved and it is not currentlly
                    # in the DB. Let's insert it!
                    # add label to osg_location
                    # add srid
                    names, values, auxs = [],[],[]
                    names.append('srid')
                    values.append(offsetSRID[0][-1])
                    # add location
                    for c in ('x', 'y', 'z', 'h', 'p', 'r'):
                        if c in ao.keys():
                            names.append(c)
                            values.append(ao.get(c))
                    auxs = []
                    try:
                        values[values.index('x')] += offsetSRID[0]
                        values[values.index('y')] += offsetSRID[1]
                        values[values.index('z')] += offsetSRID[2]
                    except ValueError:
                        logger.error('No location x,y,z found')
                    
                    for i in range(len(names)):
                        auxs.append('%s')
                    # fill OSG_LOCATION
                    OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                                    'r', 'cast_shadow']
                    fill_DB_table(names, values, auxs, OSG_LOCATION_list, 'OSG_LOCATION',
                                cursor)
                    osgLocationId = cursor.fetchone()[0]
                    
                    # add object to the DB
                    auxs = ['%s', '%s', '%s']
                    names = ['item_id', 'object_number', 'osg_location_id']
                    ITEM_OBJECT_list = ['item_id', 'object_number']
                    OSG_ITEM_OBJECT_list = ['item_id', 'object_number', 'osg_location_id']
                    values = [itemId, ObjectId, osgLocationId]
                    fill_DB_table(names, values, auxs, ITEM_OBJECT_list, 'ITEM_OBJECT', cursor)                        
                    fill_DB_table(names, values, auxs, OSG_ITEM_OBJECT_list, 'OSG_ITEM_OBJECT', cursor)
                else:
                    # log error if object is not found in DB
                    logger.error('Update not possible. OSG_ITEM_OBJECT ' +
                                str(uniqueName) + ' not found in DB')

    # Process deletes (only possible for site objects)
    deleteAOS = data.xpath('//*[@status="deleted"]')
    # loop over all deletes found in the xml config file
    for ao in deleteAOS:
        #(aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        #getDetails(ao)
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) = \
            utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType==None:
            logger.warning('add warning')
        else:
            if aoType in (utils.AO_TYPE_OBJ, utils.AO_TYPE_LAB):
                # check if the object is in the DB
                inDB = getOSGLocationId(cursor, ao, aoType, labelName, itemId,
                                        objectId)
                if inDB:
                    # update the DB with the information in the xml config file
                    deleteSiteObject(cursor, ao, aoType, labelName, itemId,
                                    objectId)
                else:
                    # log error if object is not found in DB
                    logger.warn('Not possible to delete.. OSG_ITEM_OBJECT ' +
                                str(uniqueName) +
                                ' not found in DB. Maybe already deleted?')
            else:
                # log error if trying to delete a non-site object
                logger.error('Ignoring delete in ' + uniqueName +
                            ': Meshes, pictures and PCs can not be deleted')

    # Process new objects (only possible for site objects)
    newAOS = data.xpath('//*[@status="new"]')
    # loop over all new objects found in the xml config file
    for ao in newAOS:
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) = utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType==None:
            logger.warning('warning')
        else:
            if aoType in (utils.AO_TYPE_OBJ, utils.AO_TYPE_LAB):
                # check if the object is in the DBbesafe i
                inDB = getOSGLocationId(cursor, ao, aoType, labelName, itemId, ObjectId)
                if inDB:
                    # log error if the new object is already in the DB
                    logger.warning('OSG_ITEM_OBJECT ' + str(uniqueName) +
                                ' already in DB. Ignoring add ' + uniqueName)
                else:
                    # add label to osg_location
                    # add srid
                    names, values, auxs = [],[],[]
                    names.append('srid')
                    values.append(offsetSRID[0][-1])
                    # add location
                    for c in ('x', 'y', 'z', 'h', 'p', 'r'):
                        if c in ao.keys():
                            names.append(c)
                            values.append(ao.get(c))
                    auxs = []
                    try:
                        values[values.index('x')] += offsetSRID[0]
                        values[values.index('y')] += offsetSRID[1]
                        values[values.index('z')] += offsetSRID[2]
                    except ValueError:
                        logger.error('No location x,y,z found')
                    
                    for i in range(len(names)):
                        auxs.append('%s')
                    # fill OSG_LOCATION
                    OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                                    'r', 'cast_shadow']
                    fill_DB_table(names, values, auxs, OSG_LOCATION_list, 'OSG_LOCATION',
                                cursor)
                    osgLocationId = cursor.fetchone()[0]
                    
                    if aoType == utils.AO_TYPE_OBJ:
                        # add object to the DB
                        #utils.addSiteObject(cursor, itemId, ObjectId, proto)
                        auxs = ['%s', '%s', '%s']
                        names = ['item_id', 'object_number', 'osg_location_id']
                        ITEM_OBJECT_list = ['item_id', 'object_number']
                        OSG_ITEM_OBJECT_list = ['item_id', 'object_number', 'osg_location_id']
                        values = [itemId, ObjectId, osgLocationId]
                        fill_DB_table(names, values, auxs, ITEM_OBJECT_list, 'ITEM_OBJECT', cursor)                        
                        fill_DB_table(names, values, auxs, OSG_ITEM_OBJECT_list, 'OSG_ITEM_OBJECT', cursor)

                    else:                        
                        # add label to the DB
                        utils.dbExecute(cursor, 'INSERT INTO OSG_LABEL ' +
                                        '(osg_label_name, osg_location_id, text, red, green, ' +
                                        'blue, rotate_screen, outline, font) ' +
                                        'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                        [uniqueName, osgLocationId, ao.get('labelText'),
                                        ao.get('labelColorRed'),
                                        ao.get('labelColorGreen'),
                                        ao.get('labelColorBlue'),
                                        ao.get('labelRotateScreen'),
                                        ao.get('outline'), ao.get('Font'), ])
                    ## update the information in the DB
                    #updateSetting(cursor, ao, aoType, labelName, itemId, ObjectId)
            else:
                # log error if trying to add a non-site object
                logger.error('Ignoring new in ' + uniqueName +
                            ': Meshes, pictures and PCs can not be added')

    # Process the cameras (the DEF CAMs are added for all objects
    # and can not be deleted or updated)
    cameras = data.xpath('//camera[not(starts-with(@name,"' +
                         utils.DEFAULT_CAMERA_PREFIX + '"))]')
    # get a list of cameras from the db
    data,rows = utils.fetchDataFromDB(
        cursor, 'SELECT osg_camera_name, osg_location_id FROM OSG_CAMERA')
    # only execute if there are non default cameras in the DB
    if len(data) > 0:
    # remove all cameras that are in DB
        # convert list of tuples into two lists
        camerasInDB,camerasInDBId = map(list, zip(*data))
        for i in range(0,len(camerasInDB)):
            # delete from osg_item_camera
            utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_CAMERA WHERE ' +
                                'osg_camera_name=%s', [camerasInDB[i]])                                                                                         
            # delete from osg_camera
            utils.dbExecute(cursor, 'DELETE FROM OSG_CAMERA WHERE ' +
                                'osg_camera_name=%s', [camerasInDB[i]])
            # delete from osg_location
            utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE ' +
                                'osg_location_id=%s', [camerasInDBId[i]])
    # add all cameras
    for camera in cameras:
        name = camera.get('name')
        names = ['osg_camera_name', ]
        values = [name, ]
        if name.count(utils.USER_CAMERA):
            try:
                siteId = int(name[name.index(utils.USER_CAMERA) +
                                  len(utils.USER_CAMERA):].split('_')[0])
                names.append('item_id')
                values.append(siteId)
            except:
                logger.warn('Incorrect e name:' + name)
        # add srid
        names.append('srid')
        values.append(offsetSRID[0][-1])
        # add location
        for c in ('x', 'y', 'z', 'h', 'p', 'r'):
            if c in camera.keys():
                names.append(c)
                values.append(camera.get(c))
        auxs = []
        try:
            values[values.index('x')] += offsetSRID[0]
            values[values.index('y')] += offsetSRID[1]
            values[values.index('z')] += offsetSRID[2]
        except ValueError:
            logger.error('No location x,y,z found')
        for i in range(len(names)):
            auxs.append('%s')
        # fill OSG_LOCATION
        OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                         'r', 'cast_shadow']
        fill_DB_table(names, values, auxs, OSG_LOCATION_list, 'OSG_LOCATION',
                      cursor)
        osgLocationId = cursor.fetchone()[0]
        names.append('osg_location_id')
        values.append(osgLocationId)
        auxs.append('%s')
        # fill OSG_CAMERA
        OSG_CAMERA_list = ['osg_camera_name', 'osg_location_id']
        fill_DB_table(names, values, auxs, OSG_CAMERA_list, 'OSG_CAMERA',
                      cursor)
        # fill OSG_ITEM_CAMERA
        OSG_ITEM_CAMERA_list = ['item_id', 'osg_camera_name'] 
        fill_DB_table(names, values, auxs, OSG_ITEM_CAMERA_list,
                      'OSG_ITEM_CAMERA', cursor)
    # close DB connection
    utils.closeConnectionDB(connection, cursor)
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logger.info(msg)

def get_SRID(data, cursor):
    '''
    get the offset and srid for the background used in the conf.xml file
    '''
    staticobj = [os.path.dirname(x.get('url')) for x in
                 data.xpath('//staticObject')]
    matching = [s for s in staticobj if 'PC/BACK/' in s]
    if len(matching) != 1:
        raise Exception('More than 1 background detected in xml file')
    else:
        offsetSRID, numitems = utils.fetchDataFromDB(
            cursor, 'SELECT ' +
            'offset_x, offset_y, offset_z, srid FROM OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM ON OSG_DATA_ITEM_PC_BACKGROUND.raw_data_item_id=RAW_DATA_ITEM.raw_data_item_id WHERE OSG_DATA_ITEM_PC_BACKGROUND.abs_path=%s', [os.path.join(utils.DEFAULT_DATA_DIR,utils.DEFAULT_OSG_DATA_DIR,matching[0])])
    return offsetSRID


def fill_DB_table(itemList, valueList, auxList, dbTable, dbTableName, cursor):
    '''
    Fill a DB table using dbTable and dbTableName and values provided as
    argument to the function
    '''
    # intersection of itemList with OSG_LOCATION_list
    addItemNames = list(set(itemList) & set(dbTable))
    # index of addItemNames in itemList
    addIndex = [itemList.index(item) for item in addItemNames]
    # extract required values using the index
    addItemValues = nparray(valueList)[addIndex].tolist()
    addItemAuxs = nparray(auxList)[addIndex].tolist()
    # Add item to OSG_LOCATTION DB table
    if dbTableName == 'OSG_LOCATION':
        utils.dbExecute(cursor, 'INSERT INTO ' + dbTableName + ' (' + 
                        ','.join(addItemNames) +
                        ') VALUES (' + ','.join(addItemAuxs) +
                        ') returning osg_location_id', addItemValues)
    else:
        utils.dbExecute(cursor, 'INSERT INTO ' + dbTableName + ' (' +
                        ','.join(addItemNames) +
                        ') VALUES (' + ','.join(addItemAuxs) +
                        ')', addItemValues) 
    return 1

def update_DB_table(itemList, valueList, auxList, dbTable, dbTableName, cursor):
    '''
    Fill a DB table using dbTable and dbTableName and values provided as
    argument to the function
    '''
    # intersection of itemList with OSG_LOCATION_list
    addItemNames = list(set(itemList) & set(dbTable))
    # index of addItemNames in itemList
    addIndex = [itemList.index(item) for item in addItemNames]
    # extract required values using the index
    addItemValues = nparray(valueList)[addIndex].tolist()
    addItemAuxs = nparray(auxList)[addIndex].tolist()
    # Add item to OSG_LOCATTION DB table
    utils.dbExecute(cursor, 'UPDATE ' + dbTableName + ' SET (' +
                        ','.join(addItemNames) +
                        ') = (' + ','.join(addItemAuxs) +
                        ')', addItemValues) 
    return 1

if __name__ == "__main__":
    # define argument menu
    description = "Updates DB from the changes in the XML configuration file"
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i', '--config', help='XML configuration file',
                        action='store', required=True)
    parser.add_argument('-d', '--dbname', default=utils.DEFAULT_DB,
                        help='Postgres DB name [default ' + utils.DEFAULT_DB +
                        ']', action='store')
    parser.add_argument('-u', '--dbuser', default=utils.USERNAME,
                        help='DB user [default ' + utils.USERNAME + ']',
                        action='store')
    parser.add_argument('-p', '--dbpass', default='', help='DB pass',
                        action='store')
    parser.add_argument('-t', '--dbhost', default='', help='DB host',
                        action='store')
    parser.add_argument('-r', '--dbport', default='', help='DB port',
                        action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
