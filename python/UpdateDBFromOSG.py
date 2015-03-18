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

import os, time, argparse, psycopg2, utils, logging
from lxml import etree as ET
from numpy import array as nparray

def insertDB(cursor, tableName, names, values, returnColumn = None):
    """ Generic method to insert a row in a table"""
    auxs = []
    for i in range(len(names)):
        auxs.append('%s')
    insertStatement = 'INSERT INTO ' + tableName + ' (' + ','.join(names) +') VALUES (' + ','.join(auxs) + ')'
    insertValues = values[:]
    if returnColumn != None:
        insertStatement += ' RETURNING ' + returnColumn
    utils.dbExecute(cursor, insertStatement, insertValues)
    if returnColumn != None:
        return cursor.fetchone()[0]
    else:
        return None

def getBackgroundOffset(data, cursor):
    ''' Get the offset and srid for the background used in the conf.xml file  '''
    staticobj = [os.path.dirname(x.get('url')) for x in
                 data.xpath('//staticObject')]
    matching = [s for s in staticobj if 'PC/BACK/' in s]
    if len(matching) != 1:
        raise Exception('More than 1 background detected in xml file')
    else:
        rows, numitems = utils.fetchDataFromDB(cursor, """
SELECT offset_x, offset_y, offset_z, srid 
FROM OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM USING (raw_data_item_id)
WHERE OSG_DATA_ITEM_PC_BACKGROUND.abs_path=%s""", 
[os.path.join(utils.DEFAULT_DATA_DIR,utils.DEFAULT_OSG_DATA_DIR,matching[0])])
    return rows[0]

def getOSGLocationId(cursor, aoType, labelName = None, itemId = None, objectId = None, rawDataItemId = None):
    ''' Function to get OSG location id of an Active Object related DB entry '''
    if aoType == utils.AO_TYPE_OBJ:
        if (itemId == None) or (objectId == None):
            raise Exception ('Item Object operations require not null itemId and objectId')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_ITEM_OBJECT WHERE item_id = %s AND object_number = %s', [itemId, objectId])
    elif aoType == utils.AO_TYPE_LAB:
        if labelName == None:
            raise Exception ('Label operations require not null labelName')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM OSG_LABEL WHERE osg_label_name = %s', [labelName,])
    else:
        if rawDataItemId == None:
            raise Exception ('Raw data item operations require not null rawDataItemId')
        rows, num_rows = utils.fetchDataFromDB(cursor, 'SELECT osg_location_id FROM ((SELECT * FROM OSG_DATA_ITEM_PC_SITE) UNION (SELECT * FROM OSG_DATA_ITEM_MESH) UNION (SELECT * FROM OSG_DATA_ITEM_PICTURE)) A JOIN OSG_DATA_ITEM USING (osg_data_item_id) WHERE raw_data_item_id = %s', [rawDataItemId, ])
    if num_rows == 0:
        return None
    else:
        return rows[0][0]
    
def parseLocation(cursor, xml_element, bgSRID, bgOffset):
    """ Get the names and values for a DB insert/update statement from a xml_element with location info (camera or setting)"""
    names = []
    values = []
    # Add srid
    names.append('srid')
    values.append(bgSRID)
    # Add location parameters
    for c in ('x', 'y', 'z', 'xs', 'ys', 'zs', 'h', 'p', 'r'):
        if c in xml_element.keys():
            names.append(c)
            values.append(float(xml_element.get(c)))
    # Add cast_shadow is it is present
    if 'castShadow' in xml_element.keys():
        names.append('cast_shadow')
        values.append(False if (xml_element.get('castShadow') == '0') else 1)
    # Add the offset of the background in order to store absolute coordinates in the DB   
    try:
        values[names.index('x')] += bgOffset[0]
        values[names.index('y')] += bgOffset[1]
        values[names.index('z')] += bgOffset[2]
    except ValueError:
        logging.error('No location x,y,z found')
    return (names, values)

def updateOSGLocation(cursor, osgLocationId, xml_element, bgSRID, bgOffset):
    """ Update an OSG location by its osgLocationId"""
    (names, values) = parseLocation(cursor, xml_element, bgSRID, bgOffset)
    auxs = []
    for i in range(len(values)):
        auxs.append('%s')
    utils.dbExecute(cursor, 'UPDATE OSG_LOCATION SET (' + ','.join(names) + ') = (' + ','.join(auxs) + ') WHERE osg_location_id = %s', values + [osgLocationId,]) 

def insertOSGLocation(cursor, xml_element, bgSRID, bgOffset):
    """Inserts a OSG location and returns a osgLocationId"""
    (names, values) = parseLocation(cursor, xml_element, bgSRID, bgOffset)
    return insertDB(cursor, 'OSG_LOCATION', names, values, returnColumn = 'osg_location_id')
    
def deleteOSG(cursor, aoType, labelName = None, itemId = None, objectId = None, rawDataItemId = None):
    ''' Function to delete a and OSG item objects or an OSG label (and their related OSG location entries) '''
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

def deleteCameras(cursor):
    utils.dbExecute(cursor, 'DELETE FROM OSG_ITEM_CAMERA CASCADE')
    utils.dbExecute(cursor, 'DELETE FROM OSG_CAMERA CASCADE')

def main(opts):
    # Define logging and start logging
    logname = os.path.basename(opts.config).split('.')[0] + '.log'
    utils.start_logging(filename=logname, level=opts.log)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logging.info(msg)

    # Parse xml configuration file
    data = ET.parse(opts.config).getroot()

    # Database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport)

    # get offset and srid of the background defined in the conf file
    (bgOffsetX, bgOffsetY, bgOffsetZ, bgSRID) = getBackgroundOffset(data, cursor)
    bgOffset = (bgOffsetX, bgOffsetY, bgOffsetZ)
    # Process updates
    updateAOS = data.xpath('//*[@status="updated"]')
    # loop over all updates found in the xml config file
    for ao in updateAOS:
        #(aoType, proto, uniqueName, siteId, activeobjectId, objectNumber) = \
        #getDetails(ao)
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) = utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType == None:
            msg = 'Ignoring operation on %s. Could not decode uniqueName' % uniqueName
            print msg
            logging.warning(msg)
        else:
            # check if the object is in the DB
            osgLocationId = getOSGLocationId(cursor, aoType, labelName, itemId, objectId, rawDataItemId)
            if osgLocationId != None:
                # update the DB with the information in the xml config file
                msg = 'Updating OSG location %d from %s' % (osgLocationId, uniqueName)
                print msg
                logging.info(msg)
                updateOSGLocation(cursor, osgLocationId, ao.getchildren()[0], bgSRID, bgOffset)
            else:
                if aoType == utils.AO_TYPE_OBJ:
                    # It is a bounding that has been moved and it is not currently in the DB. Let's insert it!
                    msg = 'Adding missing ITEM_OBJECT (%d,%d)' % (itemId, objectId)
                    print msg
                    logging.info(msg)
                    insertDB(cursor, 'ITEM_OBJECT', ('item_id', 'object_number'), (itemId, objectId))
                    osgLocationId = insertOSGLocation(cursor, ao.getchildren()[0], bgSRID, bgOffset)
                    insertDB(cursor, 'OSG_ITEM_OBJECT', ('item_id', 'object_number', 'osg_location_id'), (itemId, objectId, osgLocationId))
                else:
                    # log error if object is not found in DB
                    msg = 'Update not possible. OSG_ITEM_OBJECT from %s not found in DB' % uniqueName
                    print msg
                    logging.error(msg)

    # Process deletes (only possible for site objects)
    deleteAOS = data.xpath('//*[@status="deleted"]')
    # loop over all deletes found in the xml config file
    for ao in deleteAOS:
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) =  utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType==None:
            msg = 'Ignoring operation on %s. Could not decode uniqueName' % uniqueName
            print msg
            logging.warning(msg)
        else:
            if aoType in (utils.AO_TYPE_OBJ, utils.AO_TYPE_LAB):
                # check if the object is in the DB
                osgLocationId = getOSGLocationId(cursor, aoType, labelName, itemId, objectId)
                if osgLocationId != None:
                    # Delete the OSG-related entries from the DB
                    msg = 'Deleting OSG related entries for %s' % uniqueName
                    print msg
                    logging.info(msg)
                    deleteOSG(cursor, aoType, labelName, itemId, objectId)
                else:
                    # log error if object is not found in DB
                    msg = 'Not possible to delete. OSG_ITEM_OBJECT from %s not found in DB. Maybe already deleted?' % uniqueName
                    print msg
                    logging.warning(msg)
            else:
                # log error if trying to delete a non-site object
                msg = 'Ignoring delete in %s: Meshes, pictures and PCs can not be deleted' % uniqueName
                print msg
                logging.error(msg)

    # Process new objects (only possible for site objects)
    newAOS = data.xpath('//*[@status="new"]')
    # loop over all new objects found in the xml config file
    for ao in newAOS:
        uniqueName = ao.get('uniqueName')
        (aoType, itemId, rawDataItemId, objectId, labelName) = utils.decodeOSGActiveObjectUniqueName(cursor, uniqueName)
        if aoType==None:
            msg = 'Ignoring operation on %s. Could not decode uniqueName' % uniqueName
            print msg
            logging.warning(msg)
        else:
            if aoType in (utils.AO_TYPE_OBJ, utils.AO_TYPE_LAB):
                # check if the object is in the DBbesafe i
                osgLocationId = getOSGLocationId(cursor, aoType, labelName, itemId, objectId)
                if osgLocationId != None:
                    # log error if the new object is already in the DB
                    msg = 'OSG_ITEM_OBJECT from %s already in DB. Ignoring add' % uniqueName
                    print msg
                    logging.warning(msg)
                else:
                    osgLocationId = insertOSGLocation(cursor, ao.getchildren()[0], bgSRID, bgOffset)
                    if aoType == utils.AO_TYPE_OBJ:
                        # add object to the DB
                        msg = 'Adding ITEM_OBJECT (%d,%d)' % (itemId, objectId)
                        print msg
                        logging.info(msg)
                        insertDB(cursor, 'ITEM_OBJECT', ('item_id', 'object_number'), (itemId, objectId))
                        insertDB(cursor, 'OSG_ITEM_OBJECT', ('item_id', 'object_number', 'osg_location_id'), (itemId, objectId, osgLocationId))
                    else:                        
                        # add label to the DB
                        msg = 'Adding label %s' % uniqueName
                        print msg
                        logging.info(msg)
                        insertDB(cursor, 'OSG_LABEL', ('osg_label_name', 'osg_location_id', 'text', 'red', 'green', 'blue', 'rotate_screen', 'outline', 'font'), 
                                 (labelName, osgLocationId, ao.get('labelText'), 
                                  ao.get('labelColorRed'), ao.get('labelColorGreen'), ao.get('labelColorBlue'), 
                                  ao.get('labelRotateScreen'), ao.get('outline'), ao.get('Font')))
            else:
                # log error if trying to add a non-site object
                msg = 'Ignoring new in %s: Meshes, pictures and PCs can not be added' % uniqueName
                print msg
                logging.error(msg)

    # Process the cameras (the DEF CAMs are added for all objects and can not be deleted or updated)
    cameras = data.xpath('//camera[not(starts-with(@name,"' + utils.DEFAULT_CAMERA_PREFIX + '"))]')
    # Delete all previous cameras and related entries
    deleteCameras(cursor)
    # add all cameras
    for camera in cameras:
        name = camera.get('name')
        itemId = None
        if name.count(utils.USER_CAMERA):
            try:
                itemId = int(name[name.index(utils.USER_CAMERA) + len(utils.USER_CAMERA):].split('_')[0])
            except:
                msg = 'Incorrect name %s for a ITEM camera' % name
                print msg
                logging.warn(msg)
                itemId = None
        msg = 'Adding camera %s' % name
        print msg
        logging.info(msg)
        osgLocationId = insertOSGLocation(cursor, camera, bgSRID, bgOffset)
        insertDB(cursor, 'OSG_CAMERA', ('osg_camera_name', 'osg_location_id'), (name, osgLocationId))
        if itemId != None:
            insertDB(cursor, 'OSG_ITEM_CAMERA', ('item_id', 'osg_camera_name'), (itemId, name))
    # close DB connection
    utils.closeConnectionDB(connection, cursor)
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logging.info(msg)

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
