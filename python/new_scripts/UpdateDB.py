#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, time, logging, glob
import utils
import liblas

DATA_FOLDER = ''
DB_NAME = ''
TYPES = 'rop'
DATA_ITEM_TYPES_CHARS = 'pmi'
USERNAME = ''
SITE_BACKGROUND_ID = -1

LOG_LEVELS = ('DEBUG','INFO','WARNING','ERROR')
DEFAULT_LOG_LEVEL = LOG_LEVELS[0]

# Get time when we start the update process
initialTime = utils.getCurrentTime()
#Declare variable for global cursor to DB
cursor = None
dataAbsPath = None

def getDataItemTypes(ditypes):
    dataItemtypes = []
    if 'p' in ditypes:
        dataItemtypes.append(PC_FT)
    if 'm' in ditypes:
        dataItemtypes.append(MESH_FT)
    if 'i' in ditypes:
        dataItemtypes.append(PIC_FT)
        
def readLASInfo(absPath):
    """ Gets information of the LAS/LAZ files in the asbPath"""
    (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz) =  (None, 0, None, None, None, None, None, None, None)
    if os.path.isdir(absPath):
        lasfiles = glob.glob(absPath + '/*las')
        lazfiles = glob.glob(absPath + '/*laz')
        
        if len(lasfiles) >= len(lazfiles):
            extension = 'las'
        else:
            extension = 'laz'
       
        for lfile in lasfiles + lazfiles:
            lasHeader = liblas.file.File(lfile, mode='r').header
            numberPoints += lasHeader.get_pointrecordscount()
            [lminx, lminy, lminz] = lasHeader.get_min()
            if minx == None or lminx < minx:
                minx = lminx 
            if miny == None or lminy < miny:
                miny = lminy
            if minz == None or lminz < minz:
                minz = lminz
            
            [lmaxx, lmaxy, lmaxz] = lasHeader.get_max()
            if maxx == None or lmaxx > maxx:
                maxx = lmaxx
            if maxy == None or lmaxy > maxy:
                maxy = lmaxy
            if maxz == None or lmaxz > maxz:
                maxz = lmaxz
        
    else: #It is a single file
        if asbPath.lower.endswith('las'):
            extension = 'las'
        elif asbPath.lower.endswith('laz'):
            extension = 'laz'
        lasHeader = liblas.file.File(absPath, mode='r').header
        numberPoints = lasHeader.get_pointrecordscount()
        [minx, miny, minz] = lasHeader.get_min()
        [maxx, maxy, maxz] = lasHeader.get_max()
        
    return (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz)

def readPictureInfo(absPath):
    (srid, x, y, z, dx, dy, dz) = (None, None, None, None, None, None, None)
    return (srid, x, y, z, dx, dy, dz)

def is8BitColor(absPath):
    name = os.path.basename(absPath) 
    return name.count('_8BC') > 0
    
def isAligned(absPath):
    name = os.path.basename(absPath) 
    aligned = name.count('_ALIGNED_') > 0
    backgroundAligned = None
    if aligned:
        backgroundAligned = name[name.index('_ALIGNED_')+len('_ALIGNED_'):].replace('_8BC','').split('.')[0]
    return (aligned, backgroundAligned)

def isThumbnail(absPath):
    name = os.path.basename(absPath) 
    return name.lower().count('_thumb') > 0

def isCurrent(absPath):
    return (os.path.basename(os.path.abspath(absPath + '/../..')) == CURR_FT)
    
def main(opts):
    # Set logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, opts.log))
    # Establish connection with DB
    global cursor
    global dataAbsPath
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    dataItemTypes = getDataItemTypes(opts.ditypes)
    
    # The data path
    dataAbsPath = os.path.abspath(opts.data)
    
    rawDataAbsPath = dataAbsPath + '/' + RAW_FT
    osgDataAbsPath = dataAbsPath + '/' + OSG_FT
    potDataAbsPath = dataAbsPath + '/' + POT_FT
    
    if 'r' in opts.types:
        process(rawDataAbsPath, dataItemTypes, addRawDataItem)
    
    if 'o' in opts.types:
        process(osgDataAbsPath, dataItemTypes, addOSGDataItem)
    
    if 'p' in opts.types:
        process(potDataAbsPath, dataItemTypes, addPOTDataItem)
    
    if 'p' in opts.types:
        cleanPOTree(potDataAbsPath, dataItemTypes)
    
    if 'o' in opts.types:
        cleanOSG(osgDataAbsPath, dataItemTypes)
    
    if 'r' in opts.types:
        cleanRaw(rawDataAbsPath, dataItemTypes)

    if 'o' in opts.types:
        os.system('touch ' + osgDataAbsPath + '/LAST_MOD')

    cursor.close()
    coonection.close()

def process(absPath, dataItemTypes, addDataItemMethod):
    for dataItemType in (PC_FT, MESH_FT, PIC_FT):
        if dataItemType in dataItemTypes:
            disAbsPath =  absPath + '/' + dataItemType
            bdisAbsPath = disAbsPath + '/' + BG_FT
            sdisAbsPath = disAbsPath + '/' + SITE_FT
    
            if dataItemType == PC_FT:
                processBackgrounds(bdisAbsPath, addDataItemMethod, dataItemType)
                processSites(sdisAbsPath, addDataItemMethod, dataItemType)
            else:
                processBackgrounds(bdisAbsPath + '/' + CURR_FT , addDataItemMethod, dataItemType)
                processSites(sdisAbsPath + '/' + CURR_FT , addDataItemMethod, dataItemType)
                if dataItemType == MESH_FT:
                    processBackgrounds(bdisAbsPath + '/' + ARCREC_FT , addDataItemMethod, dataItemType)
                    processSites(sdisAbsPath + '/' + ARCREC_FT , addDataItemMethod, dataItemType)
                else:
                    processBackgrounds(bdisAbsPath + '/' + HIST_FT , addDataItemMethod, dataItemType)
                    processSites(sdisAbsPath + '/' + HIST_FT , addDataItemMethod, dataItemType)
                
def processBackgrounds(absPath, addMethod, dataItemType):
    t0 = time.time()
    logging.info('Processing ' + absPath)
    backgrounds = os.listdir(absPath)
    for background in backgrounds:
        addMethod(absPath + '/' + background, SITE_BACKGROUND_ID, dataItemType)
    logging.info('Processing ' + absPath + ' finished in %.2f' % (time.time() - t0))

def processSites(absPath, addMethod, dataItemType):
    t0 = time.time()
    logging.info('Processing ' + absPath)
    sites = os.listdir(absPath)
    for site in sites:
        siteId = int(site.replace('S',''))
        siteAbsPath = absPath + '/' + site
        sitePCs = os.listdir(siteAbsPath)
        for sitePC in sitePCs:
            addMethod(siteAbsPath + '/' + sitePC, siteId, dataItemType)
    logging.info('Processing ' + absPath + ' finished in %.2f' % (time.time() - t0))

def cleanRaw(rawDataAbsPath, dataItemTypes):
    logging.info('Cleaning raw data items...') 
    if PC_FT in dataItemTypes:
        utils.dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PC B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute('SELECT count(*) FROM ALIGNED_RAW_DATA_ITEM_MESH WHERE raw_data_item_pc_background_id = %s', [rawDataItemId,])
                num_dependancies = cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM ALIGNED_RAW_DATA_ITEM_PC WHERE raw_data_item_pc_background_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM POTREE_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PC_SITE WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PC_BACKGROUND WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                
                if num_dependancies == 0:
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                    utils.dbExecute(cursor, 'DELETE FROM ALIGNED_RAW_DATA_ITEM_PC WHERE raw_data_item_pc_site_id = %s', [rawDataItemId, ])
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
    if MESH_FT in dataItemTypes:
        utils.dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_MESH B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies = cursor.fetchone()[0]
                if num_dependancies == 0:
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
        
    if PIC_FT in dataItemTypes:
        utils.dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PICTURE B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies = cursor.fetchone()[0]
                if num_dependancies == 0:
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                    utils.dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!') 

def addRawDataItem(absPath, itemId, dataItemType):
    modTime = utils.getCurrentTime(utils.getLastModification(absPath))
    utils.dbExecute(cursor, 'SELECT raw_data_item_id, last_mod FROM RAW_DATA_ITEM WHERE abs_path = %s', [absPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        utils.dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM (raw_data_item_id, item_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING raw_data_item_id", 
                        [itemId, absPath, modTime, initialTime])
        rawDataItemId = cursor.fetchone()[0]
        
        if dataItemType == PC_FT:
            current = isCurrent(absPath)
            (aligned, backgroundAligned) = isAligned(absPath)
            color8bit = is8BitColor(absPath)
            (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz) = readLASInfo(absPath)  
            
            utils.dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PC (raw_data_item_id, srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        elif dataItemType == MESH_FT:
            current = isCurrent(absPath)
            (aligned, backgroundAligned) = isAligned(absPath)
            utils.dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_MESH (raw_data_item_id, current_mesh) VALUES (%s,%s)", 
                            [rawDataItemId, current])
        else:
            current = isCurrent(absPath)
            thumbnail = isThumbnail(absPath)
            (srid, x, y, z, dx, dy, dz) = readPictureInfo(absPath)
            
            utils.dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PICTURE (raw_data_item_id, current_picture, thumbnail, srid, x, y, z, dx, dy, dz) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, current, thumbnail, srid, x, y, z, dx, dy, dz])
        
        if dataItemType in (PC_FT, MESH_FT):
            if aligned:
                backgroundPath = dataAbsPath + '/' + RAW_FT + '/' + PC_FT + '/' + BG_FT + '/' + backgroundAligned
                utils.dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [backgroundPath,])
                row = cursor.fetchone()
                if row == None:
                    logging.error('Specified background in alignment of ' + absPath + ' not found!')
                else:
                    backgroundId = row[0]
                    if dataItemType == PC_FT:
                        utils.dbExecute(cursor, "INSERT INTO ALIGNED_RAW_DATA_ITEM_PC (raw_data_item_pc_site_id, raw_data_item_pc_background_id) VALUES (%s,%s)", 
                            [rawDataItemId, backgroundId])
                    else: #MESH
                        utils.dbExecute(cursor, "INSERT INTO ALIGNED_RAW_DATA_ITEM_MESH (raw_data_item_mesh_site_id, raw_data_item_pc_background_id) VALUES (%s,%s)", 
                            [rawDataItemId, backgroundId])
    else:
        (rawDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            utils.dbExecute(cursor, 'UPDATE RAW_DATA_ITEM SET (last_mod, last_check) = (%s, %s) WHERE raw_data_item_id = %s', [modTime, initialTime, rawDataItemId])
            if dataItemType == PC_FT:
                (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz) = readLASInfo(pcAbsPath)        
                utils.dbExecute(cursor, "UPDATE RAW_DATA_ITEM_PC SET (srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz) = (%s,%s,%s,%s,%s,%s,%s,%s,%s) WHERE raw_data_item_id = %s", 
                        [srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit, rawDataItemId])
            elif dataItemType == PIC_FT:
                (srid, x, y, z, dx, dy, dz) = readPictureInfo(absPath)
                utils.dbExecute(cursor, "UPDATE RAW_DATA_ITEM_PICTURE SET (srid, x, y, z, dx, dy, dz) = (%s,%s,%s,%s,%s,%s,%s) WHERE raw_data_item_id = %s", 
                        [srid, x, y, z, dx, dy, dz, rawDataItemId])
            # Note in meshes there is no need to update anything: only current may have changed and in that case it would actually mean that we have a new raw_data_item
        else: # Data has not changed. Just update checkTime
            utils.dbExecute(cursor, 'UPDATE RAW_DATA_ITEM SET last_check=%s WHERE raw_data_item_id = %s', [initialTime, rawDataItemId])

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Updates the DB from the content of the data folder"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--data',default=DATA_FOLDER,help='Data folder [default ' + DATA_FOLDER + ']',type='string')
    op.add_option('-t','--types',default=TYPES,help='What types of data is to be updated? r for RAW, o for OSG, p for POTREE [default all is checked, i.e. ' + TYPES + ']',type='string')
    op.add_option('-e','--ditypes',default=DATA_ITEM_TYPES_CHARS,help='What types of data items are updated (for the types of data selected with option types)? p for point clouds, m for meshes, i for images [default all is checked, i.e. ' + DATA_ITEM_TYPES_CHARS + ']',type='string')
    op.add_option('-d','--dbname',default=DEFAULT_DB,help='Postgres DB name where to store the geometries [default ' + DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=USERNAME,help='DB user [default ' + USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-l','--log',help='Logging level (choose from ' + ','.join(LOG_LEVELS) + ' ; default ' + DEFAULT_LOG_LEVEL + ')',type='choice', choices=LOG_LEVELS, default=DEFAULT_LOG_LEVEL)
    (opts, args) = op.parse_args()
    main(opts)
