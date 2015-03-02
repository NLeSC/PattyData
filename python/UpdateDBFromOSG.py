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

import os
import argparse
import psycopg2
import utils
import viewer_conf_api
from lxml import etree as ET
from numpy import array as nparray

logger = None
cursor = None

def getDetails(ao):
    proto = ao.get('prototype')
    uniqueName = ao.get('uniqueName')
    fs = uniqueName.split('_')
    siteId = None
    objectNumber = None
    activeObjectId = None
    if len(fs) > 1 and (fs[1] in ('pc', 'mesh', 'pic', 'OBJECT')):
        siteId = int(fs[0])
        aoType = fs[1]
        if aoType == 'obj':
            objectNumber = int(fs[2])
        else:
            activeObjectId = int(fs[2])
    else:
        aoType = 'lab'
    return (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber)


def deleteSiteObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId,
                     objectNumber):
    '''
    Function to delete a site object
    '''
    if aoType == 'obj':
        # extract osg_location_id of the object
        data,rows = utils.fetchDataFromDB(
            cursor, 'SELECT osg_location_id FROM ' +
            'OSG_ITEM_OBJECT WHERE item_id = %s AND object_number = %s',
            [siteId, objectNumber])        
        utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_OBJECT ' +
                        'WHERE item_id = %s AND object_number = %s',
                        [siteId, objectNumber])
        # delete from OSG_LOCATION
        utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE ' +
                        'osg_location_id=%s', [data[0])
        
    elif aoType == 'lab':
        # extract osg_location_id of the label
        data, rows = utils.fetchDataFromDB(
            cursor, 'SELECT osg_location_id FROM OSG_LABEL WHERE ' +
            'osg_label_name = %s', [uniqueName])
        # delete from OSG_LABEL
        utils.dbExecute(cursor,
                        'DELETE FROM OSG_LABEL WHERE osg_label_name = %s',
                        [uniqueName])
        # delete from OSG_LOCATION
        utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE ' +
                        'osg_location_id=%s', [data[0])        
    else:
        raise Exception('Not possible to delete object ' + uniqueName)


def checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                      activeObjectId, objectNumber):
    ''' 
    Function to check if the object exists in the DB 
    '''
    if aoType == 'obj':
        utils.fetch(cursor, 'SELECT * FROM OSG_ITEM_OBJECT ' +
                        'WHERE item_id = %s AND object_number = %s',
                        [siteId, objectNumber])
    elif aoType == 'lab':
        utils.dbExecute(cursor, 'SELECT * FROM OSG_LABEL ' +
                        'WHERE osg_label_name = %s', [uniqueName])
    else:
        utils.dbExecute(cursor, 'SELECT * FROM OSG_DATA_ITEM ' +
                        'WHERE item_id = %s', [activeObjectId, ])
    if not cursor.rowcount:
        return False
    return True


def updateSetting(cursor, ao, aoType, uniqueName, siteId, activeObjectId,
                  objectNumber):
    s = ao.getchildren()[0]
    names = []
    auxs = []
    values = []
    # add srid
    names.append('srid')
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
    
    # update the position of the object in OSG_LOCATION table
    OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                         'r', 'cast_shadow']
    update_DB_table(names, values, auxs, OSG_LOCATION_list, 'OSG_LOCATION',
                      cursor)
    ## extract osg_location_id and append
    #osgLocationId = cursor.fetchone()[0]
    #names.append('osg_location_id')
    #values.append(osgLocationId)
    #auxs.append('%s')    
    return 1



def main(opts):
    # Define logger and start logging
    global logger
    logger = utils.start_logging(filename=opts.config + '.log', level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script UpdateDBFromOSG.py')
    logger.info('#######################################')

    # Parse xml configuration file
    data = ET.parse(opts.config).getroot()

    # Database connection
    global cursor
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)

    # get offset and srid of the background defined in the conf file
    offsetSRID = get_SRID(data, cursor)
    
    # Process updates
    updateAOS = data.xpath('//*[@status="updated"]')
    # loop over all updates found in the xml config file
    for ao in updateAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        # check if the object is in the DB
        inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                 activeObjectId, objectNumber)
        if inDB:
            # update the DB with the information in the xml config file
            updateSetting(cursor, ao, aoType, uniqueName, siteId,
                          activeObjectId, objectNumber)
        else:
            # log error if object is not found in DB
            logger.error('Update not possible. OSG_ITEM_OBJECT ' +
                         str(uniqueName) + ' not found in DB')

    # Process deletes (only possible for site objects)
    deleteAOS = data.xpath('//*[@status="deleted"]')
    # loop over all deletes found in the xml config file
    for ao in deleteAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        if aoType in ('obj', 'lab'):
            # check if the object is in the DB
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                     activeObjectId, objectNumber)
            if inDB:
                # update the DB with the information in the xml config file
                deleteSiteObject(cursor, ao, aoType, uniqueName, siteId,
                                 activeObjectId, objectNumber)
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
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        if aoType in ('obj', 'lab'):
            # check if the object is in the DBbesafe i
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                     activeObjectId, objectNumber)
            if inDB:
                # log error if the new object is already in the DB
                logger.warning('OSG_ITEM_OBJECT ' + str(uniqueName) +
                               ' already in DB. Ignoring add ' + uniqueName)
            else:
                if aoType == 'obj':
                    # add object to the DB
                    utils.addSiteObject(cursor, siteId, objectNumber, proto)
                else:
                    # add label to the DB
                    utils.dbExecute(cursor, 'INSERT INTO OSG_LABEL ' +
                                    '(osg_label_name, text, red, green, ' +
                                    'blue, rotatescreen, outline, font) ' +
                                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                                    [uniqueName, ao.get('labelText'),
                                     ao.get('labelColorRed'),
                                     ao.get('labelColorGreen'),
                                     ao.get('labelColorBlue'),
                                     ao.get('labelRotateScreen'),
                                     ao.get('outline'), ao.get('Font'), ])
                # update the information in the DB
                updateSetting(cursor, ao, aoType, uniqueName, siteId,
                              activeObjectId, objectNumber)
        else:
            # log error if trying to add a non-site object
            logger.error('Ignoring new in ' + uniqueName +
                         ': Meshes, pictures and PCs can not be added')

    # Process the cameras (the DEF CAMs are added for all objects
    # and can not be deleted or updated)
    # TODO?: get a list of updated items -> delete/re-add them
    cameras = data.xpath('//camera[not(starts-with(@name,"' +
                         utils.DEFAULT_CAMERA_PREFIX + '"))]')
    # get a list of cameras from the db
    data,rows = utils.fetchDataFromDB(
        cursor, 'SELECT osg_camera_name, osg_location_id FROM OSG_CAMERA')
    # only execute if there are non default cameras in the DB
    if len(data) > 0:
        # convert list of tuples into two lists
        camerasInDB,camerasInDBId = map(list, zip(*data))
        # cameras in DB that are not conf file need to be removed
        camerasInConf = [camera.get('name') for camera in cameras]
        camerasRemove = list(set(camerasInDB) - set(camerasInConf))
        # index of camerasRemove in camerasInDB
        delIndex = [camerasInDB.index(item) for item in camerasRemove]
        # extract matching osg_location_id for camera names
        camerasRemoveId = nparray(camerasInDBId)[delIndex].tolist()
        # loop over all the cameras that need to be deleted
        for i in range(0,len(camerasRemove)):
            # delete from osg_item_camera
            utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_CAMERA WHERE ' +
                            'osg_camera_name=%s', [camerasRemove[i]])                                                                                         
            # delete from osg_camera
            utils.dbExecute(cursor, 'DELETE FROM OSG_CAMERA WHERE ' +
                            'osg_camera_name=%s', [camerasRemove[i]])
            # delete from osg_location
            utils.dbExecute(cursor, 'DELETE FROM OSG_LOCATION WHERE ' +
                            'osg_location_id=%s', [camerasRemoveId[i]])
        # Add all new cameras to the DB
        # list of cameras to add
        camerasAdd = list(set(camerasInConf) - set(camerasInDB))
        # index of camerasRemove in camerasInDB
        AddIndex = [camerasInDB.index(item) for item in camerasAdd]
        camerasToAdd = nparray(cameras)[AddIndex].tolist()
    else: 
        # all cameras in config are new and need to be added
        camerasToAdd = cameras
        
    for camera in camerasToAdd:
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
                logger.warn('Incorrect camera name:' + name)
        # add srid
        names.append('srid')
        values.append(offsetSRID[0][-1])
        # add location
        for c in ('x', 'y', 'z', 'h', 'p', 'r'):
            if c in camera.keys():
                names.append(c)
                values.append(camera.get(c))
        auxs = []
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
    if dbTableName == 'OSG_LOCATION':
        utils.dbExecute(cursor, 'UPDATE ' + dbTableName + ' (' + 
                        ','.join(addItemNames) +
                        ') VALUES (' + ','.join(addItemAuxs) +
                        ') returning osg_location_id', addItemValues)
    else:
        utils.dbExecute(cursor, 'UPDATE ' + dbTableName + ' (' +
                        ','.join(addItemNames) +
                        ') VALUES (' + ','.join(addItemAuxs) +
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
