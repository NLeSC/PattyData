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


def getDetails(ao):
    proto = ao.get('prototype')
    uniqueName = ao.get('uniqueName')
    fs = uniqueName.split('_')
    siteId = None
    objectNumber = None
    activeObjectId = None
    if len(fs) > 1 and (fs[1] in ('pc', 'mesh', 'pic', 'obj')):
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
    if aoType == 'obj':
        utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_OBJECT ' +
                        'WHERE item_id = %s AND object_number = %s',
                        [siteId, objectNumber])
    elif aoType == 'lab':
        utils.dbExecute(cursor,
                        'DELETE FROM OSG_LABEL WHERE osg_label_name = %s',
                        [uniqueName])
    else:
        raise Exception('Not possible to delete object ' + uniqueName)


def checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                      activeObjectId, objectNumber):
    if aoType == 'obj':
        utils.dbExecute(cursor, 'SELECT * FROM OSG_ITEM_OBJECT ' +
                        'WHERE item_id = %s AND object_number = %s',
                        [siteId, objectNumber])
    elif aoType == 'lab':
        utils.dbExecute(cursor, 'SELECT * FROM OSG_LABEL ' +
                        'WHERE osg_label_name = %s', [uniqueName])
    else:
        utils.dbExecute(cursor, 'SELECT * FROM OSG_ITEM_OBJECT ' +
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
    for c in ('x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p', 'r'):
        if c in s.keys():
            names.append(c)
            auxs.append('%s')
            values.append(s.get(c))
    if 'castShadow' in s.keys():
        names.append('cast_shadow')
        auxs.append('%s')
        values.append(False if (s.get('castShadow') == '0') else 1)

    if aoType == 'obj':
        tableName = 'OSG_ITEM_OBJECT'
        whereStatement = 'item_id = %s and object_number = %s'
        valuesWhere = [siteId, objectNumber]
    elif aoType == 'lab':
        tableName = 'OSG_LABEL'
        whereStatement = 'osg_label_name = %s'
        valuesWhere = [uniqueName, ]
    else:
        tableName = 'OSG_ITEM_OBJECT'
        whereStatement = 'osg_location_id = %s'
        valuesWhere = [activeObjectId, ]
    utils.dbExecute(cursor, 'UPDATE ' + tableName +
                    ' SET (' + ','.join(names) +
                    ') = (' + ','.join(auxs) + ') WHERE ' +
                    whereStatement, values + valuesWhere)


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
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)

    # Process updates
    updateAOS = data.xpath('//*[@status="updated"]')
    for ao in updateAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                 activeObjectId, objectNumber)
        if inDB:
            updateSetting(cursor, ao, aoType, uniqueName, siteId,
                          activeObjectId, objectNumber)
        else:
            logger.error('Update not possible. OSG_ITEM_OBJECT ' +
                         str(uniqueName) + ' not found in DB')

    # Process deletes (only possible for site objects)
    deleteAOS = data.xpath('//*[@status="deleted"]')
    for ao in deleteAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        if aoType in ('obj', 'lab'):
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                     activeObjectId, objectNumber)
            if inDB:
                deleteSiteObject(cursor, ao, aoType, uniqueName, siteId,
                                 activeObjectId, objectNumber)
            else:
                logger.warn('Not possible to delete.. OSG_ITEM_OBJECT ' +
                            str(uniqueName) +
                            ' not found in DB. Maybe already deleted?')
        else:
            logger.error('Ignoring delete in ' + uniqueName +
                         ': Meshes, pictures and PCs can not be deleted')

    # Process new objects (only possible for site objects)
    newAOS = data.xpath('//*[@status="new"]')
    for ao in newAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = \
        getDetails(ao)
        if aoType in ('obj', 'lab'):
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId,
                                     activeObjectId, objectNumber)
            if inDB:
                logger.warning('OSG_ITEM_OBJECT ' + str(uniqueName) +
                               ' already in DB. Ignoring add ' + uniqueName)
            else:
                if aoType == 'obj':
                    utils.addSiteObject(cursor, siteId, objectNumber, proto)
                else:
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
                updateSetting(cursor, ao, aoType, uniqueName, siteId,
                              activeObjectId, objectNumber)
        else:
            logger.error('Ignoring new in ' + uniqueName +
                         ': Meshes, pictures and PCs can not be added')

    # Process the cameras (the DEF CAMs are added for all objects
    # and can not be deleted or updated)
    cameras = data.xpath('//camera[not(starts-with(@name,"' +
                         utils.DEFAULT_CAMERA_PREFIX + '"))]')
    utils.dbExecute(cursor, 'DELETE FROM OSG_CAMERA')
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
                logger.warn('Incorrect camera name:' + name)
        # add srid
        offsetSRID = get_SRID(data, cursor)
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
        fill_OSG_LOCATION(names, values, auxs, cursor)
        import pdb; pdb.set_trace()
        #utils.dbExecute(cursor, 'INSERT INTO OSG_LOCATION (' + ','.join(names[2:]) +
        #                ') VALUES (' + ','.join(auxs[2:]) + ') returning osg_location_id', values[2:])
        #cursor.fetchone()[0]
        #utils.dbExecute(cursor, 'INSERT INTO OSG_CAMERA (' + ','.join(names[0]) +
        #                ') VALUES (' + ','.join(auxs[0]) + ')', values[0])            
        #utils.dbExecute(cursor, 'INSERT INTO OSG_CAMERA (' + ','.join(names[0]) +
        #                ') VALUES (' + ','.join(auxs[0]) + ')', values[0])            
        
        #utils.dbExecute(cursor, 'INSERT INTO OSG_ITEM_CAMERA (' + ','.join(names[0:2]) +
        #                ') VALUES (' + ','.join(auxs[0:2]) + ')', values[0:2])

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


def fill_OSG_LOCATION(itemList, valueList, auxList, cursor):
    '''
    Fill the OSG_LOCATION DB table
    '''
    OSG_LOCATION_list = ['srid', 'x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p',
                         'r', 'cast_shadow']
    # intersection of itemList with OSG_LOCATION_list
    addItemNames = list(set(itemList) & set(OSG_LOCATION_list))
    # index of addItemNames in itemList
    addIndex = [itemList.index(item) for item in addItemNames]
    # extract required values using the index
    addItemValues = nparray(valueList)[addIndex].tolist()
    addItemAuxs = nparray(auxList)[addIndex].tolist()
    # Add item to OSG_LOCATTION DB table
    utils.dbExecute(cursor, 'INSERT INTO OSG_LOCATION (' + ','.join(addItemNames) +
                    ') VALUES (' + ','.join(addItemAuxs) +
                    ') returning osg_location_id', addItemValues)
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
