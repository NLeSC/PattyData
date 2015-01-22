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
ITEMTYPES = 'pmi'
USERNAME = ''
SITE_BACKGROUND_ID = -1

LOG_LEVELS = ('DEBUG','INFO','WARNING','ERROR')
DEFAULT_LOG_LEVEL = LOG_LEVELS[0]

# Get time when we start the update process
initialTime = utils.getCurrentTime()
#Declare variable for global cursor to DB
cursor = None
dataAbsPath = None

def readLASInfo(absPath):
    """ Gets information of the LAS/LAZ files in the asbPath"""
    name = os.path.basename(absPath) 
    color8bit = name.count('_8BC') > 0
    aligned = name.count('_ALIGNED_') > 0
    backgroundAligned = None
    if aligned:
        backgroundAligned = name[name.index('_ALIGNED_')+len('_ALIGNED_'):].replace('_8BC','').split('.')[0]
    
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
        
    return (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit, aligned, backgroundAligned)

def main(opts):
    # Set logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, opts.log))
    # Establish connection with DB
    global cursor
    global dataAbsPath
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    # The data path
    dataAbsPath = os.path.abspath(opts.data)
    
    if 'r' in opts.types:
        processRaw(dataAbsPath + '/RAW', opts.itemtypes)
    
    if 'o' in opts.types:
        processOSG(dataAbsPath + '/OSG', opts.itemtypes)
    
    if 'p' in opts.types:
        processPOTree(dataAbsPath + '/POTREE', opts.itemtypes)
    
    if 'p' in opts.types:
        cleanPOTree(dataAbsPath + '/POTREE', opts.itemtypes)
    
    if 'o' in opts.types:
        cleanOSG(dataAbsPath + '/OSG', opts.itemtypes)
    
    if 'r' in opts.types:
        cleanRaw(dataAbsPath + '/RAW', opts.itemtypes)

    if 'o' in opts.types:
        os.system('touch ' + dataAbsPath + '/OSG/LAST_MOD')

    cursor.close()
    coonection.close()

def processRaw(rawAbsPath, itemtypes):
    if 'p' in itemtypes:
        # Process point clouds
        rawPCAbsPath = rawAbsPath + '/PC'
        processRawPointCloudsBackgrounds(rawPCAbsPath + '/BACKGROUND')
        processRawPointCloudsSites(rawPCAbsPath + '/SITES')
        
    if 'm' in itemtypes:
        # Process meshes
        rawMeshesAbsPath = rawAbsPath + '/MESHES'
        processRawMeshesBackgrounds(rawMeshesAbsPath + '/BACKGROUND/CURR', True)
        processRawMeshesBackgrounds(rawMeshesAbsPath + '/BACKGROUND/ARCH_REC', False)
        processRawMeshesSites(rawMeshesAbsPath + '/SITES/CURR', True)
        processRawMeshesSites(rawMeshesAbsPath + '/SITES/ARCH_REC', False)
        
    if 'i' in itemtypes:
        # Process pictures
        rawPicturesAbsPath = rawAbsPath + '/PICTURES'
        processRawPicturesBackgrounds(rawPicturesAbsPath + '/BACKGROUND/CURR', True)
        processRawPicturesBackgrounds(rawPicturesAbsPath + '/BACKGROUND/HIST', False)
        processRawPicturesSites(rawPicturesAbsPath + '/SITES/CURR', True)
        processRawPicturesSites(rawPicturesAbsPath + '/SITES/HIST', False)

def cleanRaw(rawAbsPath, itemtypes):
    if 'p' in itemtypes:
        # Clean point clouds
        logging.info('Cleaning raw point cloud in ' + bgRawPCAbsPath)
        utils.dbExecute(cursor, 'SELECT site_data_item_id, siteId, abs_path FROM SITE_DATA_ITEM, SITE_PC WHERE site_pc_id = site_data_item_id AND last_check < %s', [initialTime,])
        for (siteDataItemId, siteId, absPath) in cursor:
            if os.path.isfile(absPath) or os.path.isdir(absPath):
                logging.error('Data item in ' + absPath + ' has not been checked!')
            else: # There is not any file or folder in that location -> we try to delete all references of this one
                cursor.execute("""
                SELECT count(*) FROM 
                (SELECT site_pc_id FROM ALIGNED_SITE_MESH WHERE site_pc_id = %s
                    UNION
                SELECT site_pc_id FROM ALIGNED_SITE_PC WHERE site_pc_id = %s OR site_background_pc_id = %s
                    UNION
                SELECT site_pc_id FROM POTREE_SITE_PC_ID WHERE site_pc_id = %s
                    UNION
                SELECT site_pc_id FROM OSG_SITE_PC_ID WHERE site_pc_id = %s
                    UNION
                SELECT site_pc_id FROM OSG_SITE_BACKGROUND_PC_ID WHERE site_pc_id = %s) A
                """, [siteDataItemId, siteDataItemId, siteDataItemId, siteDataItemId, siteDataItemId, siteDataItemId])
                if cursor.fetchone()[0] == 0:
                    utils.dbExecute(cursor, 'DELETE FROM SITE_PC WHERE site_pc_id = %s', [siteDataItemId,])
                    utils.dbExecute(cursor, 'DELETE FROM ALIGNED_SITE_MESH WHERE site_pc_id = %s', [siteDataItemId,])
                    utils.dbExecute(cursor, 'DELETE FROM ALIGNED_SITE_PC WHERE site_pc_id = %s OR site_background_pc_id = %s', [siteDataItemId,siteDataItemId])
                    utils.dbExecute(cursor, 'DELETE FROM SITE_DATA_ITEM WHERE site_pc_id = %s', [siteDataItemId,])
                else:
                    logging.warning('Can not delete entry for removed ' + absPath + '. Related data items still there!')
    if 'm' in itemtypes:
        # Clean meshes
        rawMeshesAbsPath = rawAbsPath + '/MESHES'
        
    if 'i' in itemtypes:
        # Clean pictures
        rawPicturesAbsPath = rawAbsPath + '/PICTURES'

def processRawPointCloudsBackgrounds(bgRawPCAbsPath):
    t0 = time.time()
    logging.info('Processing raw point cloud backgrounds in ' + bgRawPCAbsPath)
    backgrounds = os.listdir(bgRawPCAbsPath)
    for background in backgrounds:
        backgroundAbsPath = bgRawPCAbsPath + '/' + background
        modTime = utils.getCurrentTime(utils.getLastModification(backgroundAbsPath))
        utils.dbExecute(cursor, 'SELECT site_data_item_id, last_mod FROM SITE_DATA_ITEM WHERE abs_path = %s', [backgroundAbsPath,])
        row = cursor.fetchone()
        if row == None: #This folder has been added recently
            utils.dbExecute(cursor, "INSERT INTO SITE_DATA_ITEM (site_data_item_id, site_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING site_data_item_id", 
                            [SITE_BACKGROUND_ID, backgroundAbsPath, modTime, initialTime])
            siteDataItemId = cursor.fetchone()[0]
            (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit) = readLASInfo(backgroundAbsPath)        
            utils.dbExecute(cursor, "INSERT INTO SITE_PC (site_pc_id, srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [siteDataItemId, srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        else:
            (siteDataItemId, lastModDB) = row
            if modTime > lastModDB: #Data has changed
                utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET (last_mod, last_check) = (%s, %s) WHERE site_data_item_id = %s', [modTime, initialTime, siteDataItemId])
                (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit) = readLASInfo(backgroundAbsPath)        
                utils.dbExecute(cursor, "UPDATE SITE_PC SET (srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) = (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                            [srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
            else: # Data has not changed
                utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET last_check=%s WHERE site_data_item_id = %s', [initialTime, siteDataItemId])
    logging.info('Raw point cloud backgrounds processing finished in %.2f' % (time.time() - t0))
    
def processRawPointCloudsSites(sRawAbsPath):
    t0 = time.time()
    logging.info('Processing raw point cloud sites in ' + sRawAbsPath)
    sites = os.listdir(sRawAbsPath)
    for site in sites:
        siteId = int(site.replace('S',''))
        siteAbsPath = sRawAbsPath + '/' + site
        sitePCs = os.listdir(siteAbsPath)
        for sitePC in sitePCs:
            sitePCAbsPath = siteAbsPath + '/' + sitePC
            modTime = utils.getCurrentTime(utils.getLastModification(sitePCAbsPath))
            utils.dbExecute(cursor, 'SELECT site_data_item_id, last_mod FROM SITE_DATA_ITEM WHERE abs_path = %s', [sitePCAbsPath,])
            row = cursor.fetchone()
            if row == None: #This folder has been added recently
                utils.dbExecute(cursor, "INSERT INTO SITE_DATA_ITEM (site_data_item_id, site_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING site_data_item_id", 
                                [SITE_BACKGROUND_ID, backgroundAbsPath, modTime, initialTime])
                siteDataItemId = cursor.fetchone()[0]
                (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit) = readLASInfo(backgroundAbsPath)        
                utils.dbExecute(cursor, "INSERT INTO SITE_PC (site_pc_id, srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                [siteDataItemId, srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
            else:
                (siteDataItemId, lastModDB) = row
                if modTime > lastModDB: #Data has changed
                    utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET (last_mod, last_check) = (%s, %s) WHERE site_data_item_id = %s', [modTime, initialTime, siteDataItemId])
                    (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit) = readLASInfo(backgroundAbsPath)        
                    utils.dbExecute(cursor, "UPDATE SITE_PC SET (srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) = (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                [srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
                else: # Data has not changed
                    utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET last_check=%s WHERE site_data_item_id = %s', [initialTime, siteDataItemId])
    logging.info('Raw point cloud backgrounds processing finished in %.2f' % (time.time() - t0))

def addRawPointCloud(pcAbsPath, siteId):
    modTime = utils.getCurrentTime(utils.getLastModification(pcAbsPath))
    utils.dbExecute(cursor, 'SELECT site_data_item_id, last_mod FROM SITE_DATA_ITEM WHERE abs_path = %s', [pcAbsPath,])
    row = cursor.fetchone()
    if row == None: #This folder has been added recently
        utils.dbExecute(cursor, "INSERT INTO SITE_DATA_ITEM (site_data_item_id, site_id, abs_path, last_mod, last_check) VALUES (DEFAULT,%s,%s,%s,%s) RETURNING site_data_item_id", 
                        [siteId, pcAbsPath, modTime, initialTime])
        siteDataItemId = cursor.fetchone()[0]
        (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit, aligned, backgroundAligned) = readLASInfo(pcAbsPath)        
        utils.dbExecute(cursor, "INSERT INTO SITE_PC (site_pc_id, srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                        [siteDataItemId, srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        if aligned:
            backgroundPath = dataAbsPath + '/RAW/PC/BACK' + backgroundAligned
            utils.dbExecute(cursor, 'SELECT site_data_item_id FROM SITE_DATA_ITEM WHERE abs_path = %s', [pcAbsPath,])
    else:
        (siteDataItemId, lastModDB) = row
        if modTime > lastModDB: #Data has changed
            utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET (last_mod, last_check) = (%s, %s) WHERE site_data_item_id = %s', [modTime, initialTime, siteDataItemId])
            (srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit) = readLASInfo(pcAbsPath)        
            utils.dbExecute(cursor, "UPDATE SITE_PC SET (srid, number_points, extension, minx, miny, minz, maxx, maxy, maxz, color_8bit) = (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                        [srid, numberPoints, extension, minx, miny, minz, maxx, maxy, maxz, color8bit])
        else: # Data has not changed. Just update checkTime
            utils.dbExecute(cursor, 'UPDATE SITE_DATA_ITEM SET last_check=%s WHERE site_data_item_id = %s', [initialTime, siteDataItemId])


def processRawMeshesBackgrounds(bgRawPCAbsPath):
    return
def processRawMeshesSites(sRawAbsPath):
    return    
def processRawPicturesBackgrounds(bgRawPCAbsPath):
    return
def processRawPicturesSites(sRawAbsPath):
    return    

def processOSG(rawAbsPath, itemtypes):
    if 'p' in itemtypes:
        # Process point clouds
        osgPCAbsPath = rawAbsPath + '/PC'
        processOSGPointCloudsBackgrounds(osgPCAbsPath + '/BACKGROUND')
        processOSGPointCloudsSites(osgPCAbsPath + '/SITES')
        
    if 'm' in itemtypes:
        # Process meshes
        osgMeshesAbsPath = osgAbsPath + '/MESHES'
        processOSGMeshesBackgrounds(osgMeshesAbsPath + '/BACKGROUND/CURR', True)
        processOSGMeshesBackgrounds(osgMeshesAbsPath + '/BACKGROUND/ARCH_REC', False)
        processOSGMeshesSites(osgMeshesAbsPath + '/SITES/CURR', True)
        processOSGMeshesSites(osgMeshesAbsPath + '/SITES/ARCH_REC', False)
        
    if 'i' in itemtypes:
        # Process pictures
        osgPicturesAbsPath = osgAbsPath + '/PICTURES'
        processOSGPicturesBackgrounds(osgPicturesAbsPath + '/BACKGROUND/CURR', True)
        processOSGPicturesBackgrounds(osgPicturesAbsPath + '/BACKGROUND/ARCH_REC', False)
        processOSGPicturesSites(osgPicturesAbsPath + '/SITES/CURR', True)
        processOSGPicturesSites(osgPicturesAbsPath + '/SITES/ARCH_REC', False)
        
def processOSGPointCloudsBackgrounds(bgOsgPCAbsPath):
    return
def processOSGPointCloudsSites(sOsgAbsPath):
    return    
def processOSGMeshesBackgrounds(bgOsgPCAbsPath):
    return
def processOSGMeshesSites(sOsgAbsPath):
    return    
def processOSGPicturesBackgrounds(bgOsgPCAbsPath):
    return
def processOSGPicturesSites(sOsgAbsPath):
    return

def processPOTree(potreeAbsPath, itemtypes):
    if 'p' in itemtypes:
        # Process point clouds
        potreePCAbsPath = potreeAbsPath + '/PC'
        processPOTreePointCloudsBackgrounds(potreePCAbsPath + '/BACKGROUND')
        processPOTreePointCloudsSites(potreePCAbsPath + '/SITES')
        
    if 'm' in itemtypes:
        # Process meshes
        potreeMeshesAbsPath = potreeAbsPath + '/MESHES'
        processPOTreeMeshesBackgrounds(potreeMeshesAbsPath + '/BACKGROUND/CURR', True)
        processPOTreeMeshesBackgrounds(potreeMeshesAbsPath + '/BACKGROUND/ARCH_REC', False)
        processPOTreeMeshesSites(potreeMeshesAbsPath + '/SITES/CURR', True)
        processPOTreeMeshesSites(potreeMeshesAbsPath + '/SITES/ARCH_REC', False)
        
    if 'i' in itemtypes:
        # Process pictures
        potreePicturesAbsPath = potreeAbsPath + '/PICTURES'
        processPOTreePicturesBackgrounds(potreePicturesAbsPath + '/BACKGROUND/CURR', True)
        processPOTreePicturesBackgrounds(potreePicturesAbsPath + '/BACKGROUND/HIST', False)
        processPOTreePicturesSites(potreePicturesAbsPath + '/SITES/CURR', True)
        processPOTreePicturesSites(potreePicturesAbsPath + '/SITES/HIST', False)
        
def processPOTreePointCloudsBackgrounds(bgPotreePCAbsPath):
    return
def processPOTreePointCloudsSites(sPotreeAbsPath):
    return    
def processPOTreeMeshesBackgrounds(bgPotreePCAbsPath):
    return
def processPOTreeMeshesSites(sPotreeAbsPath):
    return    
def processPOTreePicturesBackgrounds(bgPotreePCAbsPath):
    return
def processPOTreePicturesSites(sPotreeAbsPath):
    return





def processPCBackgrounds(backgroundsAbsPath, osgBackgroundsAbsPath):
    t0 = time.time()
    cursor = connection.cursor()
    logging.info('Processing PC backgrounds in ' + backgroundsAbsPath)
    backgrounds = os.listdir(backgroundsAbsPath)
    for background in backgrounds:
        backgroundAbsPath = os.path.join(backgroundsAbsPath, background)
        osgBackgroundAbsPath = os.path.join(osgBackgroundsAbsPath, background)
        extension = checkExtension(backgroundAbsPath)
        if extension != None:
            checkedTime = utils.getCurrentTime()
            modTime = utils.getCurrentTime(utils.getLastModification(backgroundAbsPath))
            utils.dbExecute(cursor, 'SELECT static_object_id, last_mod FROM backgrounds_pc WHERE pc_folder = %s', [backgroundAbsPath,])
            row = cursor.fetchone()
            if row == None: #This folder has been added recently                
                (mainOSGB, _, offsets) = createOSG(os.path.join(backgroundAbsPath, '*' + extension), osgBackgroundAbsPath, 'bg')
                if mainOSGB != None:
                    utils.dbExecute(cursor, 'INSERT INTO static_objects (static_object_id, osg_path) VALUES (DEFAULT,%s) RETURNING static_object_id', [mainOSGB,])
                    staticObjectId = cursor.fetchone()[0]
                    utils.dbExecute(cursor, 'INSERT INTO backgrounds_pc (background_pc_id, static_object_id, pc_folder, offset_x, offset_y, offset_z, last_mod) VALUES (DEFAULT, %s,%s,%s,%s,%s,%s)', [staticObjectId, backgroundAbsPath, offsets[0], offsets[1], offsets[2], modTime])
            else:
                (staticObjectId, timeStamp) = row
                if modTime > timeStamp:
                    # Data has changed, we re-create the OSG data
                    (mainOSGB, _, offsets) = createOSG(os.path.join(backgroundAbsPath, '*' + extension), osgBackgroundAbsPath, 'bg')
                    if mainOSGB != None:
                        utils.dbExecute(cursor, 'UPDATE backgrounds_pc SET (offset_x, offset_y, offset_z, last_mod) = (%s,%s,%s, %s) WHERE static_object_id = %s', [offsets[0], offsets[1], offsets[2], modTime, staticObjectId])           
                    else:
                        utils.dbExecute(cursor, 'DELETE FROM static_objects WHERE static_object_id = %s', [staticObjectId,])
                        utils.dbExecute(cursor, 'DELETE FROM backgrounds_pc WHERE static_object_id = %s', [staticObjectId,])
            
            utils.dbExecute(cursor, 'UPDATE backgrounds_pc SET last_check=%s WHERE pc_folder = %s', [checkedTime, backgroundAbsPath,])
    
    # Clean removed folders
    utils.dbExecute(cursor, 'DELETE FROM backgrounds_pc WHERE last_check < %s RETURNING static_object_id', [initialTime,])
    rows = cursor.fetchall()
    for (staticObjectId,) in rows:
        utils.dbExecute(cursor, 'DELETE FROM static_objects WHERE static_object_id = %s RETURNING osg_path', [staticObjectId,])
        osgPath = cursor.fetchone()[0]
        shutil.rmtree(os.path.dirname(osgPath))
      
    logging.info('PC backgrounds processing finished in %.2f' % (time.time() - t0))
    cursor.close()


def processSites(inType, sitesAbsPath, osgSitesAbsPath, backgroundsAbsPath = None, cleanDB = False):
    t0 = time.time()
    if inType == 'pc':
        (tableName, idCol, pathCol) = ('sites_pc', 'site_pc_id', 'pc_path')
    elif inType == 'mesh':
        (tableName, idCol, pathCol) = ('sites_meshes', 'site_mesh_id', 'obj_path')
    elif inType == 'pic':
        (tableName, idCol, pathCol) = ('sites_pictures', 'site_picture_id', 'pic_path')
    else:
        raise Exception('Unknown type ' + inType)

    cursor = connection.cursor()
    logging.info('Processing sites ' + inType + ' in ' + sitesAbsPath)
    sites = os.listdir(sitesAbsPath)
    for site in sites:
        siteAbsPath = os.path.join(sitesAbsPath, site)
        osgSiteAbsPath = os.path.join(osgSitesAbsPath, site)
        siteId = checkSiteId(siteAbsPath)
        if siteId != None:
            for f in os.listdir(siteAbsPath):
                siteElementAbsPath = os.path.join(siteAbsPath, f)
                logging.debug('Processing ' + siteElementAbsPath)
                processElement = True
                color8Bit = None
                (aligned, alignedBackgroundId, abOffsetX, abOffsetY, abOffsetZ) = (None,None,None,None,None)
                if inType == 'pc':
                    extension = siteElementAbsPath.split('.')[-1]
                    osgElementAbsPath = os.path.join(osgSiteAbsPath, f).replace('.' + extension,'')
                    color8Bit = (siteElementAbsPath.lower().count('8bitcolor') > 0)
                    (aligned, alignedBackgroundId, abOffsetX, abOffsetY, abOffsetZ) = getAlignmentInfo(cursor, siteElementAbsPath, backgroundsAbsPath)
                    if extension not in PC_EXTENSIONS:
                        logging.error('Ignoring file ' + siteElementAbsPath + ': not a valid extension (' + ','.join(PC_EXTENSIONS) + ')')
                        processElement = False
                elif inType == 'mesh':
                    objFiles = glob.glob(os.path.join(siteElementAbsPath, '*.obj'))
                    osgElementAbsPath = os.path.join(osgSiteAbsPath, f)
                    (aligned, alignedBackgroundId, abOffsetX, abOffsetY, abOffsetZ) = getAlignmentInfo(cursor, siteElementAbsPath, backgroundsAbsPath)
                    if len(objFiles) > 1:
                        logging.error('Ignoring mesh folder ' + siteElementAbsPath + ': multiple OBJ files found')
                        processElement = False
                    elif len(objFiles) == 1:
                        siteElementAbsPath = objFiles[0]
                elif inType == 'pic':
                    extension = siteElementAbsPath.split('.')[-1]
                    osgElementAbsPath = os.path.join(osgSiteAbsPath, f).replace('.' + extension,'')
                    
                if processElement:
                    checkedTime = utils.getCurrentTime()
                    modTime = utils.getCurrentTime(utils.getLastModification(siteElementAbsPath))
                    utils.dbExecute(cursor, 'SELECT active_object_site_id, last_mod FROM ' + tableName + ' WHERE ' + pathCol + ' = %s', [siteElementAbsPath,])
                    row = cursor.fetchone()
                    if row == None: # This element has been added recently
                        (mainOSGB, xmlPath, offsets) = createOSG(siteElementAbsPath, osgElementAbsPath, inType, abOffsetX, abOffsetY, abOffsetZ, color8Bit)
                        if xmlPath != None:
                            if abOffsetX != None and offsets[0] != 0:
                                (x,y,z) = (offsets[0], offsets[1], offsets[2])
                            else:
                                (x,y) = utils.getPositionFromFootprint(cursor, siteId, backgroundsAbsPath)
                                z = utils.DEFAULT_Z
                
                            utils.dbExecute(cursor, 'INSERT INTO active_objects_sites (active_object_site_id, site_id, osg_path, xml_path, x,y,z,cast_shadow) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s) RETURNING active_object_site_id', [siteId, mainOSGB, xmlPath, x, y, z, False])
                            activeObjectId = cursor.fetchone()[0]
                            colNames = [idCol, 'active_object_site_id', pathCol, 'last_mod']
                            colPatts = ['DEFAULT','%s','%s','%s']
                            colValues = [activeObjectId, siteElementAbsPath, modTime]
                            if aligned != None:
                                colNames.append('aligned')
                                colPatts.append('%s')
                                colValues.append(aligned)
                            if color8Bit != None:
                                colNames.append('color_8_bit')
                                colPatts.append('%s')
                                colValues.append(color8Bit)                        
                            utils.dbExecute(cursor, 'INSERT INTO ' + tableName + ' (' + ','.join(colNames) + ') VALUES (' + ','.join(colPatts) + ') RETURNING ' + idCol, colValues)
                            elementId = cursor.fetchone()[0]
                            if aligned:
                                utils.dbExecute(cursor, 'INSERT INTO aligned_' + tableName + ' (' + idCol + ', background_pc_id) VALUES (%s,%s)', [elementId, alignedBackgroundId])
                            updateXMLDescription(xmlPath, siteId, inType, activeObjectId, mainOSGB)
                    else:
                        (activeObjectId, timeStamp) = row
                        if modTime > timeStamp:
                            # Data has changed, we re-create the OSG data
                            (mainOSGB, xmlPath, offsets) = createOSG(siteElementAbsPath, osgElementAbsPath, inType, abOffsetX, abOffsetY, abOffsetZ, color8Bit)
                            updateXMLDescription(xmlPath, siteId, inType, activeObjectId, mainOSGB)
                            if xmlPath != None:
                                utils.dbExecute(cursor, 'UPDATE ' + tableName + ' SET last_mod = %s WHERE active_object_site_id = %s', [modTime, activeObjectId])
                                #utils.dbExecute(cursor, 'UPDATE active_objects SET (x,y,z) = (%s,%s,%s) WHERE active_object_id = %s', [offsets[0], offsets[1], offsets[2], activeObjectId])                
                            else:
                                utils.dbExecute(cursor, 'DELETE FROM active_objects_sites WHERE active_object_site_id = %s', [activeObjectId,])
                                utils.dbExecute(cursor, 'DELETE FROM ' + tableName + ' WHERE active_object_site_id = %s', [activeObjectId,])
                                # Remove possible row in aligned_sites_pc (Done by the ON DELETE CASCADE in Foreign key)
                    utils.dbExecute(cursor, 'UPDATE ' + tableName + ' SET last_check = %s WHERE ' + pathCol + ' = %s', [checkedTime, siteElementAbsPath,])    
    if cleanDB:
        #Clean removed folders
        utils.dbExecute(cursor, 'DELETE FROM ' + tableName + ' WHERE last_check < %s RETURNING active_object_site_id', [initialTime,])
        rows = cursor.fetchall()
        for (activeObjectId,) in rows:
            utils.dbExecute(cursor, 'DELETE FROM active_objects_sites WHERE active_object_site_id = %s', [activeObjectId,])
    #Clean old OSG folders that are not linked in the DBs
    if os.path.isdir(osgSitesAbsPath):
        osites = os.listdir(osgSitesAbsPath )
        for osite in osites:
            osgSiteAbsPath = os.path.join(osgSitesAbsPath, osite)
            for f in os.listdir(osgSiteAbsPath):
                osgSiteElementAbsPath = os.path.join(osgSiteAbsPath, f)
                osgFiles = sorted(glob.glob(os.path.join(osgSiteElementAbsPath,'*' + getOSGFileFormat(inType))))
                if len(osgFiles) == 0:
                    logging.info('Folder ' + osgSiteElementAbsPath + ' does not contain OSG data. Deleting it...')
                    shutil.rmtree(osgSiteElementAbsPath)
                else:
                    osgFile = osgFiles[0]
                    utils.dbExecute(cursor, 'SELECT active_object_site_id FROM active_objects_sites WHERE osg_path = %s', [osgFile,])
                    row = cursor.fetchone()
                    if row == None:
                        logging.info('Folder ' + osgSiteElementAbsPath + ' contains unlinked OSG data. Deleting it...')
                        shutil.rmtree(osgSiteElementAbsPath)
    logging.info('Sites ' + inType + ' in ' + sitesAbsPath + ' processing finished in %.2f' % (time.time() - t0))
    cursor.close()

def getAlignmentInfo(cursor, absPath, backgroundsAbsPath):
    (aligned, alignedBackgroundId, abOffsetX,abOffsetY,abOffsetZ) = ((absPath.lower().count('_aligned_') > 0), None, None, None, None)
    if aligned:
        background =  os.path.basename(absPath)[os.path.basename(absPath).lower().index('_aligned_')+len('_aligned_'):].split('.')[0]
        backgroundAbsPath = os.path.join(backgroundsAbsPath, background)
        utils.dbExecute(cursor, 'SELECT background_pc_id, offset_x, offset_y, offset_z FROM backgrounds_pc WHERE pc_folder = %s', [backgroundAbsPath,])
        row = cursor.fetchone()
        if row == None:
            logging.warn('Ignoring alignment information: unknown background ' + backgroundAbsPath)
            aligned = False
        else:
            (alignedBackgroundId, abOffsetX,abOffsetY,abOffsetZ) = row
    return (aligned, alignedBackgroundId, abOffsetX,abOffsetY,abOffsetZ)

def getOSGFileFormat(inType):
#    if inType == 'pic':
#        return 'osgt'
    return 'osgb'

def updateXMLDescription(xmlPath, siteId, inType, activeObjectId, fileName = None):
    tempFile = xmlPath + '_TEMP'
    ofile = open(tempFile,'w')
    lines = open(xmlPath,'r').readlines()
    for line in lines:
        if line.count('<description>'):
            ofile.write('    <description>' + utils.getOSGDescrition(siteId, inType, activeObjectId, os.path.basename(os.path.dirname(fileName))) + '</description>\n')
        else:
            ofile.write(line)
    os.system('rm ' + xmlPath)
    os.system('mv ' + tempFile + ' ' + xmlPath)

def createOSG(inFile, outFolder, inType, abOffsetX = None, abOffsetY = None, abOffsetZ = None, color8Bit = False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0,0,0))
    
    if os.path.exists(outFolder):
        os.system('rm -rf ' + outFolder) 
    os.makedirs(outFolder)
    
    os.chdir(os.path.dirname(inFile))
    outputPrefix = 'data'
    aligned = (abOffsetX != None)
    
    ofile = getOSGFileFormat(inType)
    if inType == 'pc':
        tmode = '--mode lodPoints --reposition'
#        outputPrefix = 'data' + os.path.basename(inFile)
    elif inType == 'mesh':
        tmode = '--mode polyMesh --convert --reposition'
    elif inType == 'bg':
        tmode = '--mode quadtree --reposition'
    elif inType == 'pic':
        tmode = '--mode picturePlane'
    
        
    command = CONVERTER_COMMAND + ' ' + tmode + ' --outputPrefix ' + outputPrefix + ' --files ' + os.path.basename(inFile)
    if color8Bit:
        command += ' --8bitColor '
    if aligned:
        command +=  ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + ' ' + str(abOffsetZ)
    
    logFile = os.path.join(outFolder,outputPrefix + '.log')
    command += ' &> ' + logFile

    logging.info(command)
    #os.system(command)
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True).communicate()
   
#     if inType == 'mesh':
#         rmcommand = 'rm -rf ' + inFile.replace('.obj', '2.obj')
#         logging.info(rmcommand)
#         os.system(rmcommand)
 
    mvcommand = 'mv ' + outputPrefix + '* ' + outFolder
    logging.info(mvcommand)
    os.system(mvcommand)
    outputPrefix += os.path.basename(inFile)

    ofiles = sorted(glob.glob(os.path.join(outFolder,'*' + ofile)))
    if len(ofiles) == 0:
        logging.error('none OSG file was generated (found in ' + outFolder + '). Check log: ' + logFile)
        mainOsgb = None
    else:
        mainOsgb = ofiles[0]
        if inType != 'bg':
            xmlfiles = glob.glob(os.path.join(outFolder,'*xml'))
            if len(xmlfiles) == 0:
                logging.error('none XML file was generated (found in ' + outFolder + '). Check log: ' + logFile)
                xmlPath = None
            else:
                xmlPath = xmlfiles[0]
                if len(xmlfiles) > 1:
                    logging.error('multiple XMLs file were generated (found in ' + outFolder + '). Using ' + xmlPath)
        txtfiles =  glob.glob(os.path.join(outFolder,'*offset.txt'))
        if len(txtfiles):
            txtFile = txtfiles[0]
            offsets = open(txtFile,'r').read().split('\n')[0].split(':')[1].split()
            for i in range(len(offsets)):
                offsets[i] = float(offsets[i]) 
        elif aligned:
            logging.warn('No offset file was found and it was expected!')
            
    return (mainOsgb, xmlPath, offsets)

def checkExtension(absPath, allowMultiple = False):
    """ Return the extension of the PC file/files in the provided folder. 
    If the path is empty or there aren't valid PC_EXTENSIONS it returns None.
    If allowMultiple is False it also returns None if there are multiple PC_EXTENSIONS.
    If allowMultiple is True it return the extension of the first PC file"""
    numFiles = len(os.listdir(absPath))
    if numFiles:
        extensions = []
        for extension in PC_EXTENSIONS:
            if len(glob.glob(os.path.join(absPath,'*'+extension))):
                extensions.append(extension)
        if len(extensions) > 1:
            if allowMultiple:
                return extensions[0]
            else:
                logging.warn('Ignoring folder ' + absPath + ': multiple valid PC_EXTENSIONS (' + ','.join(PC_EXTENSIONS) + ')')
        elif len(extensions) == 0:
            logging.warn('Ignoring folder ' + absPath + ': no data with valid PC_EXTENSIONS (' + ','.join(PC_EXTENSIONS) + ')')
        else: #len(hasPC_EXTENSIONS) == 1:
            return extensions[0]

def checkSiteId(absPath):
    try:
        siteId = int(os.path.basename(absPath))
    except:
        logging.warn('ignoring folder ' + absPath + '. Folder name must be a siteID')
        siteId = None
    return siteId

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Updates the DB from the content of the data folder"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--data',default=DATA_FOLDER,help='Data folder [default ' + DATA_FOLDER + ']',type='string')
    op.add_option('-t','--types',default=TYPES,help='What types of data is to be updated? r for RAW, o for OSG, p for POTREE [default all is checked, i.e. ' + TYPES + ']',type='string')
    op.add_option('-e','--itemtypes',default=ITEMTYPES,help='What types of data items are updated (for the types of data selected with option types)? p for point clouds, m for meshes, i for images [default all is checked, i.e. ' + ITEMTYPES + ']',type='string')
    op.add_option('-d','--dbname',default=DEFAULT_DB,help='Postgres DB name where to store the geometries [default ' + DEFAULT_DB + ']',type='string')
    op.add_option('-u','--dbuser',default=USERNAME,help='DB user [default ' + USERNAME + ']',type='string')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string')
    op.add_option('-r','--dbport',default='',help='DB port',type='string')
    op.add_option('-l','--log',help='Logging level (choose from ' + ','.join(LOG_LEVELS) + ' ; default ' + DEFAULT_LOG_LEVEL + ')',type='choice', choices=LOG_LEVELS, default=DEFAULT_LOG_LEVEL)
    (opts, args) = op.parse_args()
    main(opts)
