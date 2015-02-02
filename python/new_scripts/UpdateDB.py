#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, optparse, psycopg2, time, logging, glob, json
from utils import *
import liblas
import osgeo.osr

# TODO: Checking for addRawDataItem:
# SRID for PCs must not be null
# name of the Raw Data Item must not contain (CURR, BACK, OSG)
# All pictures must have JSON file with same name (.png.jason) with at least srid, x, y, z
# If it already exists it must raise error stating that old raw data item must be deleted

# TODO: RemoeRawDataItem should also remove the related OSG and POTREE data

TYPES = 'rop'
DATA_ITEM_TYPES_CHARS = 'pmi'

# Get time when we start the update process
initialTime = getCurrentTime()
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
    return dataItemtypes
        
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
            lsrid = readSRID(lasHeader)
            if srid == None:
                srid = lsrid
            elif srid != lsrid:
                srid = -1
            
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
        srid = readSRID(lasHeader)
        numberPoints = lasHeader.get_pointrecordscount()
        [minx, miny, minz] = lasHeader.get_min()
        [maxx, maxy, maxz] = lasHeader.get_max()
    
    if srid == None:
        logging.warn('SRID is not set in ' + absPath)
    elif srid == -1:
        logging.error('SRID is not the same in all files in ' + absPath)
        srid = None
    return (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz)

def readSRID(lasHeader):
    osrs = osgeo.osr.SpatialReference()
    osrs.SetFromUserInput(lasHeader.get_srs().get_wkt())
    #osrs.AutoIdentifyEPSG()
    return osrs.GetAttrValue( 'AUTHORITY', 1 )

def readPictureInfo(absPath):
    piDict = json.loads(open(absPath + '.json','r'))
    srid = piDict.get('srid')
    x = piDict.get('x')
    y = piDict.get('y')
    z = piDict.get('z')
    dx = piDict.get('dx')
    dy = piDict.get('dy')
    dz = piDict.get('dz')
    ux = piDict.get('ux')
    uy = piDict.get('uy')
    uz = piDict.get('uz')    
    return (srid, x, y, z, dx, dy, dz, ux, uy, uz)

def readOffsets(absPath):
    txtfiles =  glob.glob(absPath + '/*offset.txt')
    offsets = (None, None, None)
    if len(txtfiles):
        txtFile = txtfiles[0]
        offsets = open(txtFile,'r').read().split('\n')[0].split(':')[1].split()
        for i in range(len(offsets)):
            offsets[i] = float(offsets[i]) 
    return offsets

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
   
    return (absPath.count(CURR_FT) > 0)
    #return (os.path.basename(os.path.abspath(absPath + '/../..')) == CURR_FT)

def isBackground(absPath):
    return (absPath.count(BACK_FT) > 0)
    
def getBackgroundOffset(absPath, background):
    backgroundPath = dataAbsPath + '/' + OSG_FT + '/' + PC_FT + '/' + BG_FT + '/' + background
    dbExecute(cursor, 'SELECT A.offset_x, A.offset_y, A.offset_z, B.srid FROM OSG_DATA_ITEM_PC_BACKGROUND A, RAW_DATA_ITEM_PC B WHERE A.raw_data_item_id = B.raw_data_item_id AND abs_path = %s', [backgroundPath,])
    row = cursor.fetchone()
    if row == None:
        return (None, None, None, None)
    else:
        return row

def checkOSG(absPath):
    ofiles = sorted(glob.glob(absPath + '/*osgb'))
    if len(ofiles) == 0:
        return False
    else:
        return True
    
def getPOTParams(absPath):
    (numLevels, spacing) = (None, None)
    if absPath.count('level'):
        numLevels = int(a[a.index('level') + len('level'):].split('_')[0])
    if absPath.count('spacing'):
        spacing = int(a[a.index('spacing') + len('spacing'):].split('_')[0])
    return (numLevels, spacing)

        
def getXMLAbsPath(absPath):
    xmlfiles = glob.glob(os.path.join(absPath,'*xml'))
    if len(xmlfiles) == 0:
        return None
    else:
        xmlPath = xmlfiles[0]
        if len(xmlfiles) > 1:
            logging.warn('multiple XMLs file were found in ' + outFolder + '. Using ' + xmlPath)
        return xmlPath

def main(opts):
    # Set logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, opts.log))
    # Establish connection with DB
    global cursor
    global dataAbsPath
    connection = psycopg2.connect(postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
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
        cleanPOTree(dataItemTypes)
    
    if 'o' in opts.types:
        cleanOSG(dataItemTypes)
    
    if 'r' in opts.types:
        cleanRaw(dataItemTypes)

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

def cleanRaw(dataItemTypes):
    logging.info('Cleaning raw data items...') 
    if PC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PC B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
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
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                    dbExecute(cursor, 'DELETE FROM ALIGNED_RAW_DATA_ITEM_PC WHERE raw_data_item_pc_site_id = %s', [rawDataItemId, ])
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
    if MESH_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_MESH B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies = cursor.fetchone()[0]
                if num_dependancies == 0:
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
        
    if PIC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.itemId, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PICTURE B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies = cursor.fetchone()[0]
                if num_dependancies == 0:
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!') 

def cleanOSG(dataItemTypes):
    logging.info('Cleaning OSG data items...') 
    if PC_FT in dataItemTypes:
        # Background
        dbExecute(cursor, 'SELECT osg_data_item_pc_background_id, abs_path FROM OSG_DATA_ITEM_PC_BACKGROUND WHERE last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemPCBackgroundId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_PC_BACKGROUND WHERE osg_data_item_pc_background_id = %s', [osgDataItemPCBackgroundId,])
        # Sites
        dbExecute(cursor, 'SELECT A.osg_data_item_id, A.abs_path FROM OSG_DATA_ITEM A,OSG_DATA_ITEM_PC_SITE B WHERE A.osg_data_item_id = B.osg_data_item_id AND last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_PC_SITE WHERE osg_data_item_id = %s', [osgDataItemId,])
    if MESH_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.osg_data_item_id, A.abs_path FROM OSG_DATA_ITEM A,OSG_DATA_ITEM_MESH B WHERE A.osg_data_item_id = B.osg_data_item_id AND last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_MESH WHERE osg_data_item_id = %s', [osgDataItemId,])
    if PIC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.osg_data_item_id, A.abs_path FROM OSG_DATA_ITEM A,OSG_DATA_ITEM_PICTURE B WHERE A.osg_data_item_id = B.osg_data_item_id AND last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_PICTURE WHERE osg_data_item_id = %s', [osgDataItemId,])

def cleanPOT(dataItemTypes):
    logging.info('Cleaning POTREE data items...') 
    if PC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT potree_data_item_pc_id FROM POTREE_DATA_ITEM_PC WHERE last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (potreeDataItemPCId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('POTREE data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM POTREE_DATA_ITEM_PC WHERE osg_data_item_id = %s', [potreeDataItemPCId,])
                
    #if MESH_FT in dataItemTypes:
    #    pass
    #if PIC_FT in dataItemTypes:
    #    pass

def addRawDataItem(absPath, itemId, dataItemType):
    modTime = getCurrentTime(getLastModification(absPath))
    dbExecute(cursor, 'SELECT raw_data_item_id, last_mod FROM RAW_DATA_ITEM WHERE abs_path = %s', [absPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM (raw_data_item_id, item_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING raw_data_item_id", 
                        [itemId, absPath, modTime, initialTime])
        rawDataItemId = cursor.fetchone()[0]
        
        if dataItemType == PC_FT:
            current = isCurrent(absPath)
            (aligned, backgroundAligned) = isAligned(absPath)
            color8bit = is8BitColor(absPath)
            (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz) = readLASInfo(absPath)  
            
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PC (raw_data_item_id, srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        elif dataItemType == MESH_FT:
            current = isCurrent(absPath)
            (aligned, backgroundAligned) = isAligned(absPath)
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_MESH (raw_data_item_id, current_mesh) VALUES (%s,%s)", 
                            [rawDataItemId, current])
        else:
            current = isCurrent(absPath)
            thumbnail = isThumbnail(absPath)
            (srid, x, y, z, dx, dy, dz) = readPictureInfo(absPath)
            
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PICTURE (raw_data_item_id, current_picture, thumbnail, srid, x, y, z, dx, dy, dz) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, current, thumbnail, srid, x, y, z, dx, dy, dz])
        
        if dataItemType in (PC_FT, MESH_FT):
            if aligned:
                backgroundPath = dataAbsPath + '/' + RAW_FT + '/' + PC_FT + '/' + BG_FT + '/' + backgroundAligned
                dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [backgroundPath,])
                row = cursor.fetchone()
                if row == None:
                    logging.error('Specified background in alignment of ' + absPath + ' not found!')
                else:
                    backgroundId = row[0]
                    if dataItemType == PC_FT:
                        dbExecute(cursor, "INSERT INTO ALIGNED_RAW_DATA_ITEM_PC (raw_data_item_pc_site_id, raw_data_item_pc_background_id) VALUES (%s,%s)", 
                            [rawDataItemId, backgroundId])
                    else: #MESH
                        dbExecute(cursor, "INSERT INTO ALIGNED_RAW_DATA_ITEM_MESH (raw_data_item_mesh_site_id, raw_data_item_pc_background_id) VALUES (%s,%s)", 
                            [rawDataItemId, backgroundId])
    else:
        (rawDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            logging.warn('Raw data item in ' + absPath + ' may have been updated and it may not be reflected in the DB. Please use AddRawDataItem and RemoveRawDataItem scripts')
        dbExecute(cursor, 'UPDATE RAW_DATA_ITEM SET last_check=%s WHERE raw_data_item_id = %s', [initialTime, rawDataItemId])

def addOSGDataItem(absPath, itemId, dataItemType):
    modTime = getCurrentTime(getLastModification(absPath))
    
    rawAbsPath = absPath.replace(OSG_FT, RAW_FT)
    dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [rawAbsPath,])
    row = cursor.fetchone()
    if row == None:
        logging.error('Skipping ' + absPath + '. None related RAW data item found in ' + rawAbsPath)
        return
    rawDataItemId = cursor.fetchone()[0]
    
    if not checkOSG(absPath):
        logging.error('Skipping ' + absPath + '. None .osgb file found')
        return

    isPCBackground = isBackground(absPath) and (dataItemType == PC_FT)
    if isPCBackground:
        dbExecute(cursor, 'SELECT osg_data_item_pc_background_id, last_mod FROM OSG_DATA_ITEM_PC_BACKGROUND WHERE abs_path = %s', [absPath,])
    else:
        dbExecute(cursor, 'SELECT osg_data_item_id, last_mod FROM OSG_DATA_ITEM WHERE abs_path = %s', [absPath,])
    
    row = cursor.fetchone()  
    if row == None: #This folder has been added recently
        if isPCBackground:
            (offsetX, offsetY, offsetZ) = readOffsets(absPath)
            if offsetX == None:
                logging.error('Skipping ' + absPath + '. No offsets found')
                return
            dbExecute(cursor, "INSERT INTO OSG_DATA_ITEM_PC_BACKGROUND (osg_data_item_pc_background_id, raw_data_item_id, abs_path, last_mod, last_check, offset_x, offset_y, offset_z) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s)", 
                        [rawDataItemId, absPath, modTime, initialTime, offsetX, offsetY, offsetZ])
        else:
            xmlAbsPath = getXMLAbsPath(absPath)
            if xmlAbsPath == None:
                logging.error('Skipping ' + absPath + '. None XML file found')
                return
            (aligned, backgroundAligned) = isAligned(absPath)
            if aligned:
                (bOffsetX, bOffsetY, bOffsetZ, bSrid) = getBackgroundOffset(absPath, backgroundAligned)
                if bOffset == None:
                    logging.error('Skipping ' + absPath + '. None related background found')
                    return
                (offsetX, offsetY, offsetZ) = readOffsets(absPath)
                if offsetX == None:
                    logging.error('Skipping ' + absPath + '. No offsets found')
                    return
                (srid, x, y, z) = (bSrid, offsetX + bOffsetX, offsetY + bOffsetY, offsetZ + bOffsetZ) 
            else: #It is not aligned
                srid = None
                if dataItemType in (PC_FT, PIC_FT):
                    # We can get position from the raw data items
                    if dataItemType == PC_FT:
                        dbExecute(cursor, 'SELECT srid, minx + ((maxx - minx) / 2), miny + ((maxy - miny) / 2), minz + ((maxz - minz) / 2) FROM RAW_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                    else:
                        dbExecute(cursor, 'SELECT srid, x, y, z FROM RAW_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                    row = cursor.fetchone()
                    if row == None:
                        logging.error('Skipping ' + absPath + '. No related raw data item ' + dataItemType + ' found')
                        return
                    (srid, x, y, z) = row
                if srid == None: #If it is a Mesh or the values from point clouds and pictures are null
                    # we can get from the item geometry
                    dbExecute(cursor, "select Find_SRID('public', 'ITEM', 'geom'), st_x(g), st_y(g) from (select st_centroid(geometry(geom)) AS g from ITEM where item_id = %s) A", [itemId,])
                    if cursor.rowcount:
                        (srid, x, y) = cursor.fetchone()
                    else:
                        (srid, x, y) = (None, 0, 0)
                        logging.warn('Not possible to get position from footprint: footprint not found for ' + absPath)
                    z = DEFAULT_Z
                    
            dbExecute(cursor, "INSERT INTO OSG_LOCATION (osg_location_id, srid, x, y, z) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING osg_location_id", 
                    [srid, x, y, z])
            osgLocationId = cursor.fetchone()[0]
            
            dbExecute(cursor, "INSERT INTO OSG_DATA_ITEM (osg_data_item_id, osg_location_id, abs_path, xml_abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s,%s) RETURNING osg_data_item_id", 
                    [osgLocationId, absPath, xmlAbsPath, modTime, initialTime])
            osgDataItemId = cursor.fetchone()[0]
            if dataItemType == PC_FT:
                table = 'OSG_DATA_ITEM_PC_SITE' 
            elif dataItemType == MESH_FT:
                table = 'OSG_DATA_ITEM_MESH'
            else: # PIC_FT
                table = 'OSG_DATA_ITEM_PICTURE'
            dbExecute(cursor, "INSERT INTO " + table + " (osg_data_item_id, raw_data_item_id) VALUES (%s,%s)", 
                    [osgDataItemId, rawDataItemId])
    else:
        if isPCBackground:
            (osgDataItemPCBackgroundId, lastModDB) = row
            if modTime > lastModDB: #Data has changed
                logging.warn('OSG data item pc background in ' + absPath + ' may have been updated and it may not be reflected in the DB.')
            dbExecute(cursor, 'UPDATE OSG_DATA_ITEM_PC_BACKGROUND SET last_check=%s WHERE osg_data_item_pc_background_id = %s', [initialTime, osgDataItemPCBackgroundId])
        else:
            (osgDataItemId, lastModDB) = row
            if modTime > lastModDB: #Data has changed
                logging.warn('OSG data item in ' + absPath + ' may have been updated and it may not be reflected in the DB.')
            dbExecute(cursor, 'UPDATE OSG_DATA_ITEM SET last_check=%s WHERE osg_data_item_id = %s', [initialTime, osgDataItemId])

def addPOTDataItem(absPath, itemId, dataItemType):
    modTime = getCurrentTime(getLastModification(absPath))
    if dataItemType != PC_FT:
        logging.error('Skipping ' + absPath + '. Only POTREE point clouds are added')
        return
    
    rawAbsPath = absPath.replace(POT_FT, RAW_FT)
    dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [rawAbsPath,])
    row = cursor.fetchone()
    if row == None:
        logging.error('Skipping ' + absPath + '. None related RAW data item found in ' + rawAbsPath)
        return
    rawDataItemId = cursor.fetchone()[0]
    
    dbExecute(cursor, 'SELECT potree_data_item_id, last_mod FROM POTREE_DATA_ITEM_PC WHERE abs_path = %s', [absPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        (numLevels, spacing) = getPOTParams(absPath)
        dbExecute(cursor, "INSERT INTO POTREE_DATA_ITEM_PC (potree_data_item_id, raw_data_item_id, abs_path, last_mod, last_check, number_levels, spacing) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s)", 
                [rawDataItemId, absPath, modTime, initialTime, numLevels, spacing])
    else:
        (potreeDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            logging.warn('POTREE data item in ' + absPath + ' may have been updated and it may not be reflected in the DB.')
        dbExecute(cursor, 'UPDATE POTREE_DATA_ITEM_PC SET last_check=%s WHERE potree_data_item_id = %s', [initialTime, potreeDataItemId])


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
