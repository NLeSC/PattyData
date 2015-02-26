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
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
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
                names.append('site_id')
                values.append(siteId)
            except:
                logger.warn('Incorrect camera name:' + name)
        for c in ('x', 'y', 'z', 'h', 'p', 'r'):
            if c in camera.keys():
                names.append(c)
                values.append(camera.get(c))
        auxs = []
        for i in range(len(names)):
            auxs.append('%s')
        utils.dbExecute(cursor, 'INSERT INTO OSG_CAMERA (' + ','.join(names) +
                        ') VALUES (' + ','.join(auxs) + ')', values)

    # close DB connection
    utils.closeConnectionDB(connection, cursor)


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
