#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, time, calendar, logging
import psycopg2
from osgeo import osr

# Python Module containing methods used in other scripts

# key is attribute column name in main attribute tables (tbl1_site,...) 
# and values are column name and table name of column and table listing the different attribute values)
ATTRIBUTES = {'administrator':('initials', 'list_participants'),
'site_context':('site_context', 'list_site_context'),
'site_interpretation':('site_interpretation', 'list_site_interpretation'),
'condition':('condition', 'list_object_condition'),
'object_type':('object_type', 'list_object_type'),
'object_interpretation':('interpretation', 'list_object_interpretation'),
'period':('period', 'list_object_period'),
'depression_type':('depression_type', 'list_depression_type'),
'decoration_type':('decoration_type', 'list_object_decoration_type'),
'depiction':('depiction', 'list_object_depiction'),
'material_type':('material_type', 'list_object_material_type'),
'material_subtype':('material_subtype', 'list_object_material_subtype'),
'material_technique':('material_technique', 'list_object_material_technique')}

ATTRIBUTES_ORDER = ['administrator', 'site_context', 'site_interpretation', 'condition', 'object_type',  
                    'object_interpretation', 'period', 'depression_type', 'decoration_type',
                    'depiction', 'material_type', 'material_subtype', 'material_technique']


DEFAULT_DB = 'vadb'
USERNAME = os.popen('whoami').read().replace('\n','')
# Folder tags for the file structure
RAW_FT = 'RAW'
OSG_FT = 'OSG'
POT_FT = 'POTREE'
PC_FT = 'PC'
MESH_FT = 'MESH'
PIC_FT = 'PICT'
BG_FT = 'BACK'
SITE_FT = 'SITE'
CURR_FT = 'CURR'
ARCREC_FT = 'ARCH_REC'
HIST_FT = 'HIST'
# Default data directories
DEFAULT_DATA_DIR = '/home/pattydat/DATA'
DEFAULT_RAW_DATA_DIR = DEFAULT_DATA_DIR + '/RAW' 
DEFAULT_OSG_DATA_DIR = DEFAULT_DATA_DIR + '/OSG'
DEFAULT_POTREE_DATA_DIR = DEFAULT_DATA_DIR + '/POTREE'
BOUNDINGS_XML_RELATIVE = 'BOUN/volumes.prototype.xml'
DOMES_OSG_RELATIVE = 'DOME/skydome.osg'
ITEM_ID_BACKGROUND = -1
ITEM_OBJECT_NUMBER_ITEM = -1
DEFAULT_PROTO = 'Bounding Box'
DEFAULT_BACKGROUND = 'DRIVE_1_V3'
DEFAULT_BACKGROUND_FOLDER = DEFAULT_RAW_DATA_DIR + '/' + PC_FT + '/' + BG_FT + '/' + DEFAULT_BACKGROUND
SRID = 32633
DEFAULT_CAMERA_PREFIX = 'DEF_CAM_'
USER_CAMERA = 'SITE_'

# define global LOG variables
DEFAULT_LOG_LEVEL = 'debug'
LOG_LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}
LOG_LEVELS_LIST = LOG_LEVELS.keys()
#LOG_FORMAT = '%(asctime)-15s %(message)s'
LOG_FILENAME = '/tmp/patty.log'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
DATE_FORMAT = "%Y/%m/%d/%H:%M:%S"

#Ouput Formats
LAS = 'LAS'
LAZ = 'LAZ'

POTREE_SERVER_DATA_ROOT = '/home/pattydat/DATA'
POTREE_DATA_URL_PREFIX = 'http://148.251.106.132:8090'

OSG_DATA_PREFIX = 'data'

# ACTIVE OBJECT TYPES for OSG
AO_TYPE_MESH = MESH_FT
AO_TYPE_PC = PC_FT
AO_TYPE_PIC = PIC_FT
AO_TYPE_LAB = 'LAB'
AO_TYPE_OBJ = 'OBJ'

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

def connectToDB(dbName = None, userName= None, password = None, dbHost = None, dbPort = None, verbose = False):
    """ Connects to a specified DB and returns connection and cursor objects
    """       
    # Start DB connection
    try: 
        connection = psycopg2.connect(postgresConnectString(dbName, userName, password, dbHost, dbPort, False))
        
    except Exception, E:
        err_msg = 'Cannot connect to %s DB.'% dbName
        print(err_msg)
        logging.error((err_msg, "; %s: %s" % (E.__class__.__name__, E)))
        raise
        
    msg = 'Successful connection to %s DB.'%dbName
    if verbose:
        print msg
    logging.debug(msg)
    
    # if the connection succeeded get a cursor    
    cursor = connection.cursor()
        
    return connection, cursor
    
def closeConnectionDB(connection, cursor, verbose = False):
    """ Closes a connection to a DB given the connection and cursor objects
    """      
    cursor.close()
    connection.close()    
    
    msg = 'Connection to the DB is closed.'
    if verbose:
        print msg
    logging.debug(msg)
    
    return    

def countElementsTable(cursor, table):
    """ Checks and returns the number of elements in a table"""    
    num_elements= 0
    
    count_query = "SELECT COUNT(*) FROM " + table
    dbExecute(cursor, count_query)
    
    num_elements = cursor.fetchone()
    
    return num_elements
    
def typeColumnTable(cursor, column, table):
    """ Returns the PG type of a given column froma given table"""
    col_type = ''
    
    # select the column of interest from the given table
    select_column_sql = "SELECT {0} FROM {1}".format(column,table)
    
    dbExecute(cursor, select_column_sql)
    
    # get the internal PG type code
    type_code = cursor.description[0].type_code
    
    select_type_sql = "SELECT typname FROM pg_type WHERE OID=%s"%type_code
    values, nums = fetchDataFromDB(cursor, select_type_sql)
    
    col_type = values[0][0]
    
    return col_type
    
def fetchDataFromDB(cursor, query, queryArgs = None, mogrify = True, verbose = False):
    """ Fetches data from a DB, given the sursor object and the fetch query
        Return the fetched data items and their number
    """ 
    data_items = []

    try:
        dbExecute(cursor, query, queryArgs, mogrify)
    except Exception, E:
        err_msg = "Cannot execute the SQL query: %s" % cursor.mogrify(query, queryArgs)
        print(err_msg)
        logging.error((err_msg, "; %s: %s" % (E.__class__.__name__, E)))
        raise
    
    data_items = cursor.fetchall()
    
    num_items = cursor.rowcount
    
    if verbose:
        msg = 'Retrieved %s data_items.'%num_items
        print msg
        logging.debug(msg)

    return data_items, num_items    
    
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

def listRawDataItems(cursor):
    data_items, num_items = fetchDataFromDB(cursor, "SELECT raw_data_item_id, abs_path FROM RAW_DATA_ITEM ORDER BY item_id, abs_path")
    if num_items:
        m = '\t'.join(('#RawDataItemId','absPath'))
        print m
        logging.info(m)
        for (rawDataItem, absPath) in data_items:
            m = '\t'.join((str(rawDataItem),absPath))
            print m
            logging.info(m)

def start_logging(filename=LOG_FILENAME, level=DEFAULT_LOG_LEVEL):
    "Start logging with given filename and level."
    logging.basicConfig(filename=filename, level=LOG_LEVELS[level],
                        format=LOG_FORMAT, datefmt=DATE_FORMAT)
    logger = logging.getLogger(__name__)
    return logger

def readSRID(lasHeader):
    osrs = osr.SpatialReference()
    osrs.SetFromUserInput(lasHeader.get_srs().get_wkt())
    #osrs.AutoIdentifyEPSG()
    return osrs.GetAttrValue( 'AUTHORITY', 1 )

def apply_argument_parser(argumentsParser, options=None):
    """ Apply the argument parser. """
    if options is not None:
        args = argumentsParser.parse_args(options)
    else:
        args = argumentsParser.parse_args() 
    return args

def load_sql_file(cursor, sqlFile):
    success = False
    
    # set the level temporarily to autocommit
    old_isolation_level = cursor.connection.isolation_level
    cursor.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    # execute the SQL statement from the external DBdump of site object geometries
    try:
        for statement in open(sqlFile,'r').read().split(';'):
            if statement.strip() != '':
                logging.debug(statement)
                cursor.execute(statement)
    except Exception, E:
        err_msg = 'Cannot execute the commands in %s.' % sqlFile
        print(err_msg)
        logging.error(err_msg)
        logging.error(" %s: %s" % (E.__class__.__name__, E))
        raise
    
    cursor.connection.set_isolation_level(old_isolation_level)
    
    success = True
    msg = 'Successful execution of the commands in %s.' % sqlFile
#    print msg
    logging.debug(msg)
        
    return success

def codeOSGActiveObjectUniqueName(cursor, aoType, rawDataItemId = None, itemId = None, objectId = None, labelName = None ):
    """ This gets a unique name for a OSG Active Object.
    OSG Active Objects are OSG PCs, OSG Meshes, OSG pics, OSG item objects (boundings) or OSG labels
    aoType is the type of active objects. Please use AO_TYPE_MESH, AO_TYPE_PC, AO_TYPE_PIC, AO_TYPE_LAB and AO_TYPE_OBJ
    For OSG PCs, Meshes and Pics provide rawDataItemId, 
    For OSG items objects provide itemId and objectId
    For OSG labels provide label name """
    
    if aoType not in (AO_TYPE_MESH, AO_TYPE_PC, AO_TYPE_PIC, AO_TYPE_LAB, AO_TYPE_OBJ):
        raise Exception('Not valid OSG active object type!')
     
    uniqueName = ''
    if aoType in (AO_TYPE_MESH, AO_TYPE_PC, AO_TYPE_PIC):
        if rawDataItemId == None:
            raise Exception('Raw Data item ID can not be None if Active Object Type is ' + ','.join((AO_TYPE_MESH, AO_TYPE_PC, AO_TYPE_PIC)))
        rows, num = fetchDataFromDB(cursor, "SELECT item_id, abs_path FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s", [rawDataItemId,])
        if num == 1:
            (itemId, absPath) = rows[0]
            if aoType == AO_TYPE_MESH:
                aux = 'mesh'
            elif aoType == AO_TYPE_PC:
                aux = 'pc'
            else:
                aux  = 'pic'
            uniqueName = str(itemId) + '_' + aux + '_' + str(rawDataItemId) + '_' + os.path.basename(absPath)
        else:
            raise Exception('Raw Data Item with ID %d is not in DB!' % rawDataItemId)
    elif aoType == AO_TYPE_OBJ:
        if objectId == None or itemId == None:
            raise Exception('Item Id or Object ID can not be None if Active Object Type is ' + AO_TYPE_OBJ)
        uniqueName = str(itemId) + '_obj_'  + str(objectId)
    else: #LAB
        if labelName == None:
            raise Exception('Label name ID can not be None if Active Object Type is ' + AO_TYPE_LAB)
        uniqueName = 'lab_' + str(labelName)
    return uniqueName

def decodeOSGActiveObjectUniqueName(uniqueName):
    try:
        itemId = None
        rawDataItemId = None
        objectId = None
        labelName = None    
        fs = uniqueName.split('_')
        aux = fs[1]
        
        if aux == 'mesh':
            aoType = AO_TYPE_MESH
        elif aux == 'pc':
            aoType = AO_TYPE_PC
        elif aux == 'pic':
            aoType = AO_TYPE_PIC    
        elif aux == 'obj':
            aoType = AO_TYPE_OBJ
        else:
            aoType = AO_TYPE_LAB
                
        if aoType == AO_TYPE_OBJ:
            objectId = int(fs[2])
            itemId = int(fs[0])
        elif aoType == AO_TYPE_LAB:
            labelName = uniqueName[len('lab_'):]
        else:
            itemId = int(fs[0])
            rawDataItemId = int(fs[2])
        print fs, objectId
        return  (aoType, itemId, rawDataItemId, objectId, labelName)
    except Exception:
        return (None, None, None, None, None)
