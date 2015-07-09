#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, argparse, time, logging, glob, json
from utils import *
import liblas
#from osgeo import osr

# TODO: Checking for addRawDataItem:
# SRID for PCs must not be null
# name of the Raw Data Item must not contain (CURR, BACK, OSG)
# All pictures must have JSON file with same name (.png.jason) with at least srid, x, y, z
# If it already exists it must raise error stating that old raw data item must be deleted

# TODO: RemoeRawDataItem should also remove the related OSG and POTREE data

TYPES = 'ropn'
DATA_ITEM_TYPES_CHARS = 'pmi'

# Get time when we start the update process
initialTime = getCurrentTime()
#Declare variable for global cursor to DB
cursor = None

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
            
            if lasHeader.get_pointrecordscount():
            
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
        logging.info('SRID is not set in ' + absPath)
    elif srid == -1:
        logging.error('SRID is not the same in all files in ' + absPath)
        srid = None
    return (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz)

def readPictureInfo(absPath):
    if os.path.isfile(absPath + '.json'):
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
    else:
        return (None, None,None,None,None,None,None,None,None,None)

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
    return (absPath.lower().count('8bc') > 0) or (absPath.lower().count('8bit') > 0)
    
def getMeshSRID(absPath):
    srid = None
    if absPath.count('_SRID_') > 0:
        try:
            srid = int(absPath[absPath.index('_SRID_') + len('_SRID_'):].split('_')[0])
        except:
            logging.error('SRID not recognized from ' + absPath)
            srid = None
    return srid

def isThumbnail(absPath):
    return absPath.lower().count('_thumb') > 0

def isCurrent(absPath):
    return (absPath.count(CURR_FT) > 0)

def isBackground(absPath):
    return (absPath.count(BG_FT) > 0)
    
def getBackgroundOffset(srid):
    dbExecute(cursor, 'SELECT A.offset_x, A.offset_y, A.offset_z FROM OSG_DATA_ITEM_PC_BACKGROUND A, RAW_DATA_ITEM_PC B, RAW_DATA_ITEM C WHERE A.raw_data_item_id = B.raw_data_item_id AND A.raw_data_item_id = C.raw_data_item_id AND C.srid = %s', [srid,])
    row = cursor.fetchone()
    if row == None:
        return (None, None, None)
    else:
        return row

def checkOSG(absPath):
    ofiles = sorted(glob.glob(absPath + '/*osgb'))
    if len(ofiles) == 0:
        return False
    else:
        return True
    
def getPOTNumberLevels(absPath):
    numLevels = None
    if absPath.count('_levels_') > 0:
        numLevels = int(absPath[absPath.index('_levels_') + len('_levels_'):].split('_')[0])
    return numLevels

def getMTLAbsPath(absPath):
    mtlfiles = glob.glob(absPath + '/*mtl')
    if len(mtlfiles) == 0:
        return None
    else:
        mtlPath = mtlfiles[0]
        if len(mtlfiles) > 1:
            logging.warn('multiple MTLs file were found in ' + absPath + '. Using ' + mtlPath)
        return mtlPath       

def getPlyAbsPath(absPath):
    plyfiles = glob.glob(absPath + '/*ply')
    if len(plyfiles) == 0:
        return None
    else:
        plyPath = plyfiles[0]
        if len(plyfiles) > 1:
            logging.warn('multiple PLYs file were found in ' + absPath + '. Using ' + plyPath)
        return plyPath  

def getXMLAbsPath(absPath):
    xmlfiles = glob.glob(absPath + '/*xml')
    if len(xmlfiles) == 0:
        return None
    else:
        xmlPath = xmlfiles[0]
        if len(xmlfiles) > 1:
            logging.warn('multiple XMLs file were found in ' + outFolder + '. Using ' + xmlPath)
        return xmlPath

def run(opts):
    # Set logging
    logname = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    start_logging(filename=logname, level=opts.log)
    # Establish connection with DB
    global cursor
    connection, cursor = connectToDB(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport) 

    dataItemTypes = getDataItemTypes(opts.ditypes)
    
    # The data path
    dataAbsPath = os.path.abspath(opts.data)
     
    rawDataAbsPath = dataAbsPath + '/' + RAW_FT
    osgDataAbsPath = dataAbsPath + '/' + OSG_FT
    potDataAbsPath = dataAbsPath + '/' + POT_FT
    nexDataAbsPath = dataAbsPath + '/' + NEX_FT
    

    localtime = getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' %localtime
    print msg
    logging.info(msg)
    if 'r' in opts.types:
        process(rawDataAbsPath, dataItemTypes, addRawDataItem)
    
    if 'o' in opts.types:
        process(osgDataAbsPath, dataItemTypes, addOSGDataItem)
    
    if 'p' in opts.types:
        process(potDataAbsPath, dataItemTypes, addPOTDataItem)
    
    if 'n' in opts.types:
        process(nexDataAbsPath, dataItemTypes, addNEXDataItem)
    
    if 'p' in opts.types:
        cleanPOT(dataItemTypes)
    
    if 'o' in opts.types:
        cleanOSG(dataItemTypes)
    
    if 'n' in opts.types:
        cleanNEX(dataItemTypes)
    
    if 'r' in opts.types:
        cleanRaw(dataItemTypes)

    if 'o' in opts.types:
        os.system('touch ' + osgDataAbsPath + '/LAST_MOD')

    cursor.close()
    connection.close()
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (time.time() - t0, logname)
    print msg
    logging.info(msg)

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
    if not os.path.isdir(absPath):
        logging.warn('Skipping ' + absPath + '. It does not exist')
        return
    t0 = time.time()
    logging.info('Processing ' + absPath)
    backgrounds = os.listdir(absPath)
    for background in backgrounds:
        addMethod(absPath + '/' + background, ITEM_ID_BACKGROUND, dataItemType)
    logging.info('Processing ' + absPath + ' finished in %.2f' % (time.time() - t0))

def processSites(absPath, addMethod, dataItemType):
    if not os.path.isdir(absPath):
        logging.warn('Skipping ' + absPath + '. It does not exist')
        return
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
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.item_id, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PC B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                num_dependancies = 0
                cursor.execute('SELECT count(*) FROM POTREE_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PC_SITE WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_PC_BACKGROUND WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                
                if num_dependancies == 0:
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_PC WHERE raw_data_item_id = %s', [rawDataItemId,])
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
    if MESH_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.item_id, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_MESH B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (rawDataItemId, itemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Raw data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                num_dependancies = 0
                cursor.execute('SELECT count(*) FROM OSG_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                cursor.execute('SELECT count(*) FROM NEXUS_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                num_dependancies += cursor.fetchone()[0]
                if num_dependancies == 0:
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM_MESH WHERE raw_data_item_id = %s', [rawDataItemId,])
                    dbExecute(cursor, 'DELETE FROM RAW_DATA_ITEM WHERE raw_data_item_id = %s', [rawDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
        
    if PIC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.raw_data_item_id, A.item_id, abs_path FROM RAW_DATA_ITEM A, RAW_DATA_ITEM_PICTURE B WHERE A.raw_data_item_id = B.raw_data_item_id AND A.last_check < %s', [initialTime,])
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
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_PC_SITE WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])
    if MESH_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.osg_data_item_id, A.abs_path FROM OSG_DATA_ITEM A,OSG_DATA_ITEM_MESH B WHERE A.osg_data_item_id = B.osg_data_item_id AND last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_MESH WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])
    if PIC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT A.osg_data_item_id, A.abs_path FROM OSG_DATA_ITEM A,OSG_DATA_ITEM_PICTURE B WHERE A.osg_data_item_id = B.osg_data_item_id AND last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (osgDataItemId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('OSG data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM_PICTURE WHERE osg_data_item_id = %s', [osgDataItemId,])
                dbExecute(cursor, 'DELETE FROM OSG_DATA_ITEM WHERE osg_data_item_id = %s', [osgDataItemId,])

def cleanPOT(dataItemTypes):
    logging.info('Cleaning POTREE data items...') 
    if PC_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT potree_data_item_pc_id, abs_path FROM POTREE_DATA_ITEM_PC WHERE last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (potreeDataItemPCId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('POTREE data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM POTREE_DATA_ITEM_PC WHERE potree_data_item_pc_id = %s', [potreeDataItemPCId,])


def cleanNEX(dataItemTypes):
    logging.info('Cleaning NEXUS data items...') 
    if MESH_FT in dataItemTypes:
        dbExecute(cursor, 'SELECT nexus_data_item_mesh_id, abs_path FROM NEXUS_DATA_ITEM_MESH WHERE last_check < %s', [initialTime,])
        rows = cursor.fetchall()
        for (necusDataItemMeshId, absPath) in rows:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('NEXUS data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we can delete this entry
                dbExecute(cursor, 'DELETE FROM NEXUS_DATA_ITEM_MESH WHERE nexus_data_item_mesh_id = %s', [necusDataItemMeshId,])
                
def addRawDataItem(absPath, itemId, dataItemType):
    if os.path.isdir(absPath) and len(os.listdir(absPath)) == 0:
        logging.warn('Skipping ' + absPath + '. Empty directory')
        return
    modTime = getCurrentTime(getLastModification(absPath))
    dbExecute(cursor, 'SELECT raw_data_item_id, last_mod FROM RAW_DATA_ITEM WHERE abs_path = %s', [absPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        dbExecute(cursor, 'SELECT item_id FROM ITEM WHERE item_id = %s', [itemId,])
        row = cursor.fetchone()
        if row == None:
            isBack = (itemId < 0)
            dbExecute(cursor, "INSERT INTO ITEM (item_id, background) VALUES (%s,%s)", [itemId, isBack])
            if not isBack: 
                dbExecute(cursor, "INSERT INTO ITEM_OBJECT (item_id, object_number) VALUES (%s,%s)", [itemId, ITEM_OBJECT_NUMBER_ITEM])
        dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM (raw_data_item_id, item_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING raw_data_item_id", 
                        [itemId, absPath, modTime, initialTime])
        rawDataItemId = cursor.fetchone()[0]
        srid = None
        if dataItemType == PC_FT:
            current = isCurrent(absPath)
            color8bit = is8BitColor(absPath)
            (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz) = readLASInfo(absPath)  
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PC (raw_data_item_id, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        elif dataItemType == MESH_FT:
            current = isCurrent(absPath)
            srid = getMeshSRID(absPath)
            mtlAbsPath = getMTLAbsPath(absPath)
            plyAbsPath = getPlyAbsPath(absPath)
            color8bit = is8BitColor(absPath)
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_MESH (raw_data_item_id, current_mesh, mtl_abs_path, ply_abs_path, color_8bit) VALUES (%s,%s,%s,%s)", 
                            [rawDataItemId, current, mtlAbsPath, plyAbsPath, color8bit])
        else:
            current = isCurrent(absPath)
            thumbnail = isThumbnail(absPath)
            (srid, x, y, z, dx, dy, dz, ux, uy, uz) = readPictureInfo(absPath)
            dbExecute(cursor, "INSERT INTO RAW_DATA_ITEM_PICTURE (raw_data_item_id, current_picture, thumbnail, x, y, z, dx, dy, dz, ux, uy, uz) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [rawDataItemId, current, thumbnail, x, y, z, dx, dy, dz, ux, uy, uz])
        if srid != None:
            dbExecute(cursor, 'UPDATE RAW_DATA_ITEM SET srid=%s WHERE raw_data_item_id = %s', [srid, rawDataItemId])
    else:
        (rawDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            logging.warn('Raw data item in ' + absPath + ' may have been updated and it may not be reflected in the DB. Please use AddRawDataItem and RemoveRawDataItem scripts')
        dbExecute(cursor, 'UPDATE RAW_DATA_ITEM SET last_check=%s WHERE raw_data_item_id = %s', [initialTime, rawDataItemId])

def addOSGDataItem(absPath, itemId, dataItemType):
    modTime = getCurrentTime(getLastModification(absPath))
    
    rawAbsPath = absPath.replace(OSG_FT, RAW_FT)
    dbExecute(cursor, 'SELECT raw_data_item_id, srid FROM RAW_DATA_ITEM WHERE abs_path = %s', [rawAbsPath,])
    row = cursor.fetchone()
    if row == None:
        logging.error('Skipping ' + absPath + '. None related RAW data item found in ' + rawAbsPath)
        return
    (rawDataItemId, rawSRID) = row
    
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
                logging.error('Skipping ' + absPath + '. None offsets found')
                return
            dbExecute(cursor, "INSERT INTO OSG_DATA_ITEM_PC_BACKGROUND (osg_data_item_pc_background_id, raw_data_item_id, abs_path, last_mod, last_check, offset_x, offset_y, offset_z) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s)", 
                        [rawDataItemId, absPath, modTime, initialTime, offsetX, offsetY, offsetZ])
        else:
            xmlAbsPath = getXMLAbsPath(absPath)
            if xmlAbsPath == None:
                logging.error('Skipping ' + absPath + '. None XML file found')
                return
            (srid,x,y,z) = (None, 0, 0, 0)
            # We try to get the SRID and position of this OSG object
            if rawSRID != None:
                if dataItemType in (PC_FT, MESH_FT): # Only meshes and point clouds have offsets provided by OSG converter
                    # Try to get it from OSG generated offsets
                    (bOffsetX, bOffsetY, bOffsetZ) = getBackgroundOffset(rawSRID)
                    if bOffsetX == None:
                        logging.warn('OSG position of ' + absPath + ' could not be computed. None background found with same SRID')
                    else:
                        (offsetX, offsetY, offsetZ) = readOffsets(absPath)
                        if offsetX == None:
                            logging.warn('OSG position of ' + absPath + ' could not be computed. None offsets found')
                        else:
                            srid = rawSRID
                            (x, y, z) = (offsetX + bOffsetX, offsetY + bOffsetY, offsetZ + bOffsetZ)
                else: #PICTURE can use position from the RAW data item (if srid is not null it means a JSON was provided along with the pic)
                    dbExecute(cursor, 'SELECT x, y, z FROM RAW_DATA_ITEM_PICTURE WHERE raw_data_item_id = %s', [rawDataItemId,])
                    row = cursor.fetchone()
                    if row == None:
                        logging.critical('Skipping ' + absPath + '. None related raw data item ' + dataItemType + ' found')
                        return
                    srid = rawSRID
                    (x, y, z) = row
                    
            if srid == None: # If SRID of raw data item is null or the previous method did not work we can get from the item geometry
                try:
                    dbExecute(cursor, "SELECT ST_SRID(geom), st_x(st_centroid(geometry(geom))), st_y(st_centroid(geometry(geom))), min_z + ((max_z - min_z) / 2) FROM ITEM WHERE item_id = %s AND geom is NOT %s", [itemId,None])
                    if cursor.rowcount:
                        (srid, x, y, z) = cursor.fetchone()
                    else:
                        logging.warn('Not possible to get position from footprint: footprint not found for ' + absPath)
                except Exception ,e:
                    logging.error(e)
                    cursor.connection.rollback()
    
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
    if dataItemType != PC_FT:
        logging.error('Skipping ' + sAbsPath + '. Only POTREE point clouds are added')
        return
    
    rawAbsPath = absPath.replace(POT_FT, RAW_FT)
    dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [rawAbsPath,])
    row = cursor.fetchone()
    if row == None:
        logging.error('Skipping ' + absPath + '. None related RAW data item found in ' + rawAbsPath)
        return
    rawDataItemId = row[0]
    
    #  POTree can have multiple conversion per raw data item
    for sPath in os.listdir(absPath):
        sAbsPath = absPath + '/' + sPath
        modTime = getCurrentTime(getLastModification(sAbsPath))
        dbExecute(cursor, 'SELECT potree_data_item_pc_id, last_mod FROM POTREE_DATA_ITEM_PC WHERE abs_path = %s', [sAbsPath,])
        row = cursor.fetchone()
        if row == None: #This folder has been added recently
            numLevels = getPOTNumberLevels(sAbsPath)
            dbExecute(cursor, "INSERT INTO POTREE_DATA_ITEM_PC (potree_data_item_pc_id, raw_data_item_id, abs_path, last_mod, last_check, number_levels) VALUES (DEFAULT,%s,%s,%s,%s,%s)", 
                    [rawDataItemId, sAbsPath, modTime, initialTime, numLevels])
        else:
            (potreeDataItemId, lastModDB) = row
            if modTime > lastModDB: #Data has changed
                logging.warn('POTREE data item in ' + sAbsPath + ' may have been updated and it may not be reflected in the DB.')
            dbExecute(cursor, 'UPDATE POTREE_DATA_ITEM_PC SET last_check=%s WHERE potree_data_item_pc_id = %s', [initialTime, potreeDataItemId])

def addNEXDataItem(absPath, itemId, dataItemType):
    if dataItemType != MESH_FT:
        logging.error('Skipping ' + sAbsPath + '. Only Nexus meshes are added')
        return
    
    rawAbsPath = absPath.replace(NEX_FT, RAW_FT)
    dbExecute(cursor, 'SELECT raw_data_item_id FROM RAW_DATA_ITEM WHERE abs_path = %s', [rawAbsPath,])
    row = cursor.fetchone()
    if row == None:
        logging.error('Skipping ' + absPath + '. None related RAW data item found in ' + rawAbsPath)
        return
    rawDataItemId = row[0]
    
    modTime = getCurrentTime(getLastModification(absPath))
    dbExecute(cursor, 'SELECT nexus_data_item_mesh_id, last_mod FROM NEXUS_DATA_ITEM_MESH WHERE abs_path = %s', [absPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        dbExecute(cursor, "INSERT INTO NEXUS_DATA_ITEM_MESH (nexus_data_item_mesh_id, raw_data_item_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s)", 
                [rawDataItemId, absPath, modTime, initialTime])
    else:
        (nexusDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            logging.warn('NEXUS data item in ' + absPath + ' may have been updated and it may not be reflected in the DB.')
        dbExecute(cursor, 'UPDATE NEXUS_DATA_ITEM_MESH SET last_check=%s WHERE nexus_data_item_mesh_id = %s', [initialTime, nexusDataItemId])


def argument_parser():
    parser = argparse.ArgumentParser(description="Updates the DB from the content of the data folder")
    
    parser.add_argument('-i','--data',default=DEFAULT_DATA_DIR,help='Data folder [default ' + DEFAULT_DATA_DIR + ']',type=str)
    parser.add_argument('-t','--types',default=TYPES,help='What types of data is to be updated? r for RAW, o for OSG, p for POTREE [default all is checked, i.e. ' + TYPES + ']',type=str)
    parser.add_argument('-e','--ditypes',default=DATA_ITEM_TYPES_CHARS,help='What types of data items are updated (for the types of data selected with option types)? p for point clouds, m for meshes, i for images [default all is checked, i.e. ' + DATA_ITEM_TYPES_CHARS + ']',type=str)
    parser.add_argument('-d','--dbname',default=DEFAULT_DB,help='Postgres DB name [default ' + DEFAULT_DB + ']',type=str)
    parser.add_argument('-u','--dbuser',default=USERNAME,help='DB user [default ' + USERNAME + ']',type=str)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str)
    parser.add_argument('-b','--dbhost',default='',help='DB host',type=str)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str)
    parser.add_argument('--log', help='Log level', choices=LOG_LEVELS_LIST, default=DEFAULT_LOG_LEVEL)
    return parser

if __name__ == "__main__":
    try:
        checkSuperUser()
        run(apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
