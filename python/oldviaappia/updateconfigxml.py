#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=logging.DEBUG)
import utils 
import viewer_conf_api
from lxml import etree as ET

# Script to update DB from config XML changes

def getDetails(ao):
    proto = ao.get('prototype')
    uniqueName = ao.get('uniqueName')
    fs =  uniqueName.split('_')
    siteId = None
    objectNumber = None
    activeObjectId = None
    if len(fs) > 1 and (fs[1] in ('pc','mesh','pic','obj')):
        siteId = int(fs[0])
        aoType = fs[1]
        if aoType == 'obj':
            objectNumber = int(fs[2])
        else:
            activeObjectId = int(fs[2])
    else:
        aoType = 'lab'
    return (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber)

def deleteSiteObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber):
    if aoType == 'obj':
        utils.dbExecute(cursor, 'DELETE FROM active_objects_sites_objects WHERE site_id = %s AND object_id = %s', [siteId, objectNumber])
    elif aoType == 'lab':
        utils.dbExecute(cursor, 'DELETE FROM active_objects_labels WHERE name = %s', [uniqueName])
    else:
        raise Exception('Not possible to delete object ' + uniqueName)
    
def checkActiveObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber):
    if aoType == 'obj':
        utils.dbExecute(cursor, 'SELECT * FROM active_objects_sites_objects WHERE site_id = %s AND object_id = %s', [siteId, objectNumber])
    elif aoType == 'lab':
        utils.dbExecute(cursor, 'SELECT * FROM active_objects_labels WHERE name = %s', [uniqueName])
    else:
        utils.dbExecute(cursor, 'SELECT * FROM active_objects_sites WHERE active_object_site_id = %s', [activeObjectId,] )
    if not cursor.rowcount:
        return False
    return True

def updateSetting(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber):
    s = ao.getchildren()[0]
    names = []
    auxs = []
    values = []
    for c in ('x','y','z','xs','ys','zs','h','p','r'):
        if c in s.keys():
            names.append(c)
            auxs.append('%s')
            values.append(s.get(c))
    if 'castShadow' in s.keys():
        names.append('cast_shadow')
        auxs.append('%s')
        values.append(False if (s.get('castShadow') == '0') else 1)

    if aoType == 'obj':
        tableName = 'active_objects_sites_objects'
        whereStatement = 'site_id = %s and object_id = %s'
        valuesWhere = [siteId,objectNumber]
    elif aoType == 'lab':
        tableName = 'active_objects_labels'
        whereStatement = 'name = %s'
        valuesWhere = [uniqueName,]
    else:
        tableName = 'active_objects_sites'
        whereStatement = 'active_object_site_id = %s'
        valuesWhere = [activeObjectId,]
    utils.dbExecute(cursor, 'UPDATE ' + tableName + ' SET (' + ','.join(names) + ') = (' + ','.join(auxs) + ') WHERE ' + whereStatement, values + valuesWhere)

def main(opts):
    data = ET.parse(opts.config).getroot()
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    #First we do updates
    updateAOS = data.xpath('//*[@status="updated"]')
    for ao in updateAOS:    
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = getDetails(ao)
        inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
        if inDB:
            updateSetting(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
        else:
            logging.error('Update not possible. activeObject ' + str(uniqueName) + ' not found in DB')

    #Now the deletes (only possible for site objects)
    deleteAOS = data.xpath('//*[@status="deleted"]')
    for ao in deleteAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = getDetails(ao)
        if aoType in ('obj', 'lab'):
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
            if inDB:
                deleteSiteObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
            else:
                logging.warn('Not possible to delete.. activeObject ' + str(uniqueName) + ' not found in DB. Maybe already deleted?')
        else:
            logging.error('Ignoring delete in ' + uniqueName + ': Meshes, pictures and PCs can not be deleted')
    
    #Finally the new objects (only possible for site objects)
    newAOS = data.xpath('//*[@status="new"]')
    for ao in newAOS:
        (aoType, proto, uniqueName, siteId, activeObjectId, objectNumber) = getDetails(ao)
        if aoType in ('obj', 'lab'):
            inDB = checkActiveObject(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
            if inDB:
                logging.warn('activeObject ' + str(uniqueName) + ' already in DB. Ignoring add ' + uniqueName)
            else:
                if aoType == 'obj':
                    utils.addSiteObject(cursor, siteId, objectNumber, proto)
                else:
                    utils.dbExecute(cursor, 'INSERT INTO active_objects_labels (name,text,red,green,blue,rotatescreen,outline,font) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', 
                                    [uniqueName,ao.get('labelText'),ao.get('labelColorRed'),ao.get('labelColorGreen'),ao.get('labelColorBlue'),
                                     ao.get('labelRotateScreen'),ao.get('outline'),ao.get('Font'),])
                updateSetting(cursor, ao, aoType, uniqueName, siteId, activeObjectId, objectNumber)
        else:
            logging.error('Ignoring new in ' + uniqueName + ': Meshes, pictures and PCs can not be added')
            
    #Process the cameras (the DEF CAMs are added for all objects and can not be deleted or updated)
    cameras = data.xpath('//camera[not(starts-with(@name,"' + utils.DEFAULT_CAMERA_PREFIX + '"))]')
    utils.dbExecute(cursor, 'DELETE FROM cameras')
    for camera in cameras:
        name = camera.get('name')
        names = ['camera_name',]
        values = [name,]
        if name.count(utils.USER_CAMERA):
            try:
                siteId = int(name[name.index(utils.USER_CAMERA)+len(utils.USER_CAMERA):].split('_')[0])
                names.append('site_id')
                values.append(siteId)
            except:
                logging.warn('Incorrect camera name:' + name)
        for c in ('x','y','z','h','p','r'):
            if c in camera.keys():
                names.append(c)
                values.append(camera.get(c))
        auxs = []
        for i in range(len(names)):
            auxs.append('%s')
        utils.dbExecute(cursor, 'INSERT INTO cameras (' + ','.join(names) + ') VALUES (' + ','.join(auxs) + ')', values)

        
if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Updates DB from the changes in the XML configuration file"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--config',default='',help='XML configuration file',type='string')
    op.add_option('-d','--dbname',default=utils.DEFAULT_DB,help='Postgres DB name [default ' + utils.DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    (opts, args) = op.parse_args()
    main(opts)
