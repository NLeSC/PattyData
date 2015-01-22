#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, subprocess, time, calendar, logging

# Python Module containing methods used in other scripts
PROPERTIES = {'administrator':('initials', 'list_participants'),
'site_context':('site_context', 'list_site_context'),
'site_interpretation':('site_interpretation', 'list_site_interpretation'),
'condition':('condition', 'list_object_condition'),
'object_type':('object_type', 'list_object_type'),
'object_interpretation':('object_interpretation', 'list_object_interpretation'),
'period':('period', 'list_object_period'),
'reliability':('reliability', 'list_reliability'),
'depression_type':('depression_type', 'list_depression_type'),
'decoration_type':('decoration_type', 'list_object_decoration_type'),
'depiction':('depiction', 'list_object_depiction'),
'material_type':('material_type', 'list_object_material_type'),
'material_subtype':('material_subtype', 'list_object_material_subtype'),
'material_technique':('material_technique', 'list_object_material_technique')}

PROPERTIES_ORDER = ['administrator', 'site_context', 'site_interpretation', 'condition', 'object_type',  
                    'object_interpretation', 'period', 'reliability', 'depression_type', 'decoration_type',
                    'depiction', 'material_type', 'material_subtype', 'material_technique']

DEFAULT_DB = 'vadb'
USERNAME = os.popen('whoami').read().replace('\n','')
DEFAULT_RAW_DATA_FOLDER = '/home/vadata/DATA/RAW/'
DEFAULT_OSG_DATA_DIR = '/home/vadata/DATA/OSG/'
BOUNDINGS_XML_RELATIVE = 'BOUNDINGS/volumes.prototype.xml'
SITE_OBJECT_NUMBER = -1
DEFAULT_PROTO = 'Bounding Box'
DEFAULT_Z = -140
DEFAULT_BACKGROUND = 'DRIVE_1_V3'
DEFAULT_BACKGROUND_FOLDER = DEFAULT_RAW_DATA_FOLDER + 'PC/BACKGROUND/' + DEFAULT_BACKGROUND
SRID = 32633
DEFAULT_CAMERA_PREFIX = 'DEF_CAM_'
USER_CAMERA = 'SITE_'

def getLastModification(absPath, initialLMTime = None):
    """
    Get the last modification time of the provided path. 
    The returned values is the number of seconds since the epoch given in time module
    So, it is the UnixTime
    """
    lastModifiedTime = initialLMTime
    if os.path.isfile(absPath):
        t = os.path.getmtime(absPath)
        if lastModifiedTime == None or t > lastModifiedTime:
            lastModifiedTime = t
    elif os.path.isdir(absPath):
        # it is a dir
        for element in os.listdir(absPath):
            elementPath = absPath + '/' + element
            t = os.path.getmtime(elementPath)
            if lastModifiedTime == None or t > lastModifiedTime:
                lastModifiedTime = t
            if os.path.isdir(elementPath):
                t = getLastModification(elementPath, lastModifiedTime)
                if lastModifiedTime == None or t > lastModifiedTime:
                    lastModifiedTime = t
    return lastModifiedTime

def getCurrentTime(t = None):
    """
    Get current localUnixTime if t is None. Convert t to localUnixTime. 
    t is seconds since the epoch given by module time (GMT/UTC)
    localUnixTime = UnixTime + 7200 [or 3600]
    """
    return calendar.timegm(time.localtime(t))
    
def getCurrentTimeAsAscii():
    """ Return the current local time in ASCII. Use it if you want a prettyly 
        formatted time
    """    
    return time.asctime( time.localtime(time.time()) )
    
def postgresConnectString(dbName = None, userName= None, password = None, dbHost = None, dbPort = None, cline = False):
    connString=''
    if cline:    
        if dbName != None and dbName != '':
            connString += " " + dbName
        if userName != None and userName != '':
            connString += " -U " + userName
        if password != None and password != '':
            os.environ['PGPASSWORD'] = password
        if dbHost != None and dbHost != '':
            connString += " -h " + dbHost
        if dbPort != None and dbPort != '':
            connString += " -p " + dbPort
    else:
        if dbName != None and dbName != '':
            connString += " dbname=" + dbName
        if userName != None and userName != '':
            connString += " user=" + userName
        if password != None and password != '':
            connString += " password=" + password
        if dbHost != None and dbHost != '':
            connString += " host=" + dbHost
        if dbPort != None and dbPort != '':
            connString += " port=" + dbPort
    return connString

def dbExecute(cursor, query, queryArgs = None, mogrify = True):
    if queryArgs == None:
        if mogrify:
            logging.debug(cursor.mogrify(query))
        cursor.execute(query)
    else:
        if mogrify:
            logging.debug(cursor.mogrify(query, queryArgs))
        cursor.execute(query, queryArgs)
    cursor.connection.commit()
    
def getLASParams(inputFile):
    (count, minX, minY, minZ, maxX, maxY, maxZ, scaleX, scaleY, scaleZ, offsetX, offsetY, offsetZ) = (None, None, None, None, None, None, None, None, None, None, None, None, None )
    outputLASInfo = subprocess.Popen('lasinfo -i ' + inputFile  + ' -nc -nv -nco -merged', shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    for line in outputLASInfo[1].split('\n'):
        if line.count('min x y z:'):
            [minX, minY, minZ] = line.split(':')[-1].strip().split(' ')
        elif line.count('max x y z:'):
            [maxX, maxY, maxZ] = line.split(':')[-1].strip().split(' ')
        elif line.count('number of point records:'):
            count = line.split(':')[-1].strip()
        elif line.count('scale factor x y z:'):
            [scaleX, scaleY, scaleZ] = line.split(':')[-1].strip().split(' ')
        elif line.count('offset x y z:'):
            [offsetX, offsetY, offsetZ] = line.split(':')[-1].strip().split(' ')

    return (count, minX, minY, minZ, maxX, maxY, maxZ, scaleX, scaleY, scaleZ, offsetX, offsetY, offsetZ)

def getPositionFromFootprint(cursor, siteId, rawDataPath):
    bgFolder = os.path.abspath(os.path.join(rawDataPath, DEFAULT_BACKGROUND))
    cursor.execute('select offset_x, offset_y from backgrounds_pc where pc_folder = %s', [bgFolder])
    if cursor.rowcount:
        (offx,offy) = cursor.fetchone()
        cursor.execute('with a as (select st_centroid(geometry(geom)) AS g from sites_geoms where site_id = %s LIMIT 1) select st_x(g) - %s, st_y(g) - %s from a', [siteId,offx,offy])
        if cursor.rowcount:
            return cursor.fetchone()
        else:
            logging.warn('Not possible to get position from footprint: footprint not found')
    else:
        logging.error('Not possible to get position from footprint: background ' + DEFAULT_BACKGROUND + ' not found')
    return (0,0)
