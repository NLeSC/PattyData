# import general modules
from ConfigParser import ConfigParser
import os, sys, shutil, errno
from collections import namedtuple
#import itertools

# import the tested modules
testFolder = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir))
currentFolder = os.getcwd()
scriptsFolder = os.path.abspath(os.path.join(testFolder, '../python'))
sys.path.append(scriptsFolder)

import utils
import CreateDB, UpdateDBFootprints, UpdateDBAttribute, UpdateDBItemZ


# get configuration from an ini file 
def getConfig(testFolder, iniFileName):
    """ Gets configuraiton handle from an ini file """
    config = ConfigParser()
    config.optionxform=str
    config.read(os.path.abspath(os.path.join(testFolder, iniFileName )))
    
    return config

def cleanup():
# clean everything
    print "Cleaning up..."
# cleanup the local test data directory sttructure 
    if os.path.exists(dataPath):
       shutil.rmtree(dataPath)
       
    files = os.listdir(currentFolder)

    for f in files:
        if os.path.isfile(f) & f.endswith('.log'):
            print "Cleanedup log file: ", f
            os.remove(f)
# drop the test DB
    os.system('dropdb ' + utils.postgresConnectString(dbName, dbUser, dbPass, dbHost, dbPort, True))   
    #print "If exisiting:"
    print "Log files have been removed." 
    print "DATA folder has been removed."
    print "Test DB has been dropped."
    print "Cleaning up...DONE"
    print "-----------------------------------------------------------------------"

def fillOSGData(localDataPath, serverDataPath):    
    """ copies some OSG test data from the server data path to the local data path"""
    
    OSGLocalDataPath = os.path.join(localDataPath, 'OSG')
    OSGServerDataPath =os.path.join(serverDataPath, 'OSG')
    
    fillPcData(OSGLocalDataPath, OSGServerDataPath)
    fillMeshData(OSGLocalDataPath, OSGServerDataPath)
    fillPictData(OSGLocalDataPath, OSGServerDataPath)
    
def fillPcData(LocalDataPath, ServerDataPath):    
    """ copies some PC test data from the server data path to the local data path"""
    # set up some paths shortcuts
    
    PCLocalDataPath = os.path.join(LocalDataPath, 'PC')
    PCServerDataPath = os.path.join(ServerDataPath, 'PC')
    SitePCLocalDataPath = os.path.join(PCLocalDataPath, 'SITE')
    SitePCServerDataPath = os.path.join(PCServerDataPath, 'SITE')
    BGPCLocalDataPath = os.path.join(PCLocalDataPath, 'BACK')
    BGPCServerDataPath = os.path.join(PCServerDataPath, 'BACK')
    
    
    # copy OSG data    
    # 2 PC for 2 sites
    try:
        dest =  os.path.join(SitePCLocalDataPath,'S13')
        #os.mkdir(dest)
        src = os.path.join(SitePCServerDataPath,'S13')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise
            
    try:
        dest =  os.path.join(SitePCLocalDataPath,'S162')
        #os.mkdir(dest)
        src = os.path.join(SitePCServerDataPath,'S162')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise  
        
     # BG
    try:
        dest =  os.path.join(BGPCLocalDataPath,'DRIVE_1_V3')
        #os.mkdir(dest)
        src = os.path.join(BGPCServerDataPath,'DRIVE_1_V3')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise  
            
    
def fillMeshData(LocalDataPath, ServerDataPath):    
    """ copies some MESH test data from the server data path to the local data path"""
    # set up some paths shortcuts
    curr = 'CURR'
    arch = 'ARCH_REC'
    MeshLocalDataPath = os.path.join(LocalDataPath, 'MESH')
    MeshServerDataPath = os.path.join(ServerDataPath, 'MESH')
    SiteMeshLocalDataPath = os.path.join(MeshLocalDataPath, 'SITE')
    SiteMeshServerDataPath = os.path.join(MeshServerDataPath, 'SITE')
    CurrSiteMeshLocalDataPath = os.path.join(SiteMeshLocalDataPath, curr)
    CurrSiteMeshServerDataPath = os.path.join(SiteMeshServerDataPath, curr)
    ArchSiteMeshLocalDataPath = os.path.join(SiteMeshLocalDataPath, arch)
    ArchSiteMeshServerDataPath = os.path.join(SiteMeshServerDataPath, arch)
    
    
#    BGMeshLocalDataPath = os.path.join(MeshLocalDataPath, 'BACK')
#    BGMeshServerDataPath = os.path.join(MeshServerDataPath, 'BACK')
#    CurrBGMeshLocalDataPath = os.path.join(BGMeshLocalDataPath, curr)
#    CurrBGMeshServerDataPath = os.path.join(BGMeshServerDataPath, curr)    
#    ArchBGMeshLocalDataPath = os.path.join(BGMeshLocalDataPath, arch)
#    ArchBGMeshServerDataPath = os.path.join(BGMeshServerDataPath, arch)
    
    # copy  data    
    # 2 PC for 2 sites
    try:
        dest =  os.path.join(CurrSiteMeshLocalDataPath,'S13')
        #os.mkdir(dest)
        src = os.path.join(CurrSiteMeshServerDataPath,'S13')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise
            
    try:
        dest =  os.path.join(ArchSiteMeshLocalDataPath,'S162')
        #os.mkdir(dest)
        src = os.path.join(ArchSiteMeshServerDataPath,'S162')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise  
        
     # BG

def fillPictData(LocalDataPath, ServerDataPath):    
    """ copies some Pict  test data from the server data path to the local data path"""
    # set up some paths shortcuts
    curr = 'CURR'
    arch = 'HIST'
    PictLocalDataPath = os.path.join(LocalDataPath, 'PICT')
    PictServerDataPath = os.path.join(ServerDataPath, 'PICT')
    SitePictLocalDataPath = os.path.join(PictLocalDataPath, 'SITE')
    SitePictServerDataPath = os.path.join(PictServerDataPath, 'SITE')
    CurrSitePictLocalDataPath = os.path.join(SitePictLocalDataPath, curr)
    CurrSitePictServerDataPath = os.path.join(SitePictServerDataPath, curr)
    ArchSitePictLocalDataPath = os.path.join(SitePictLocalDataPath, arch)
    ArchSitePictServerDataPath = os.path.join(SitePictServerDataPath, arch)

    # copy  data

    try:
        dest =  os.path.join(CurrSitePictLocalDataPath,'S13')
        #os.mkdir(dest)
        src = os.path.join(CurrSitePictServerDataPath,'S13')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise
            
    try:
        dest =  os.path.join(ArchSitePictLocalDataPath,'S162')
        #os.mkdir(dest)
        src = os.path.join(ArchSitePictServerDataPath,'S162')
        shutil.copytree(src, dest)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else: raise  
        
def fillTestData(localDataPath, serverDataPath):
    """ copies some test data from the server data path to the local data path"""
    fillOSGData(localDataPath, serverDataPath)
    
##############################################################################
### Setup ###

# get configuration handle
print "-----------------------------------------------------------------------"
print "-------------Testing of the python scripts in PattyData----------------"
print "-----------------------------------------------------------------------"

print "Setting up..."
iniFileName = 'test.ini'

config = getConfig(testFolder, iniFileName)

# read configuration parameters
logLevel = config.get('General','LogLevel')

dbName = config.get('DB','Name')
dbHost = config.get('DB','Host')
dbUser = config.get('DB','User')
dbPass = config.get('DB','Pass')
dbPort = config.get('DB','Port')

footprints_file = config.get('Data','Footprints')
attributes_file = config.get('Data','Attributes')

footprints_item_ids = config.get('Data', 'FootprintsItemIds')
footprints_drive_map = config.get('Data', 'FootprintsDriveMap')

####
dataPath = config.get('Data','Path')
serverDataPath = config.get('Data','ServerPath')

# clean everything
if os.path.exists(dataPath):
    shutil.rmtree(dataPath)

dirs = [[dataPath],
        ['RAW','OSG','POTREE'],
        ['PC','MESH','PICT','DOME','BOUND'],
        ['BACK', 'SITE'],
        ['CURR', 'HIST', 'ARCH_REC']]
## generate a redundant(very!) common directory structure
#for item in itertools.product(*dirs):    
#    os.makedirs(os.path.join(*item))

print "Scripts input parameters loaded."    
#print "Directory structure (redundant) was created." 
print "Setting up...DONE."  
print "-----------------------------------------------------------------------"

##############################################################################
cleanup()

fillTestData(dataPath, serverDataPath)

exit(1)
# create test  DB
print "Testing creation of the DB ..."
sqlFile = os.path.abspath(os.path.join(testFolder, '../Database/ERDB.sql'))
CreateDBArguments = namedtuple("Create_DB_Arguments", "sql dbname dbuser dbpass dbhost dbport log")
CreateDB.run(CreateDBArguments(sqlFile, dbName, dbUser, dbPass, dbHost, dbPort, logLevel))
logFile = os.path.basename(sqlFile ) + '.log'
logFileContent = open(logFile,'r').read()
if logFile.count('ERROR') > 0:
    print 'ERRORs in CreateDB.py. See %s' % logFile
    cleanup()
    sys.exit()
print "The testing of the creation of the DB...DONE."
print "-----------------------------------------------------------------------"

# update the footprints
print "Testing updating the DB with the sites' footprints... "

CreateFootprArguments = namedtuple("Footpr_Arguments", "input dbname dbuser dbpass dbhost dbport")
UpdateDBFootprints.run(CreateFootprArguments(footprints_file, dbName, dbUser, dbPass, dbHost, dbPort))

logFile = os.path.basename(footprints_file) + '.log'
logFileContent = open(logFile,'r').read()

if logFile.count('ERROR') > 0:
    print 'ERRORs in updating the sites footprints. See %s' % logFile
    cleanup()
    sys.exit()
print "The testing of the footprints DB update...DONE."
print "-----------------------------------------------------------------------"

# update the attributes
print "Testing updating the Attributes in the DB... "

CreateAttrArguments = namedtuple("Attr_Arguments", "input dbname dbuser dbpass dbhost dbport log")
UpdateDBAttribute.run(CreateAttrArguments(attributes_file, dbName, dbUser, dbPass, dbHost, dbPort, logLevel))

logFile = os.path.basename(attributes_file) + '.log'
logFileContent = open(logFile,'r').read()

if logFile.count('ERROR') > 0:
    print 'ERRORs in updating the sites attributes. See %s' % logFile
    cleanup()
    sys.exit()
print "The testing of the attributes DB update...DONE."
print "-----------------------------------------------------------------------"

# update the Z of some sites
print "Testing updating the Z of given items in the DB... "

CreateZArguments = namedtuple("Z_Arguments", "itemid las dbname dbuser dbpass dbhost dbport cores")
UpdateDBItemZ.run(CreateZArguments(footprints_item_ids, footprints_drive_map, dbName, dbUser, dbPass, dbHost, dbPort, 16))

logFile = 'UpdateDBItemZ.log'
logFileContent = open(logFile,'r').read()

if logFile.count('ERROR') > 0:
    print 'ERRORs in updating the ItemIdZ. See %s' % logFile
    cleanup()
    sys.exit()
print "The testing of the updating the Z of given items in the DB...DONE."
print "-----------------------------------------------------------------------"

# UpdateDB.py
# AddRawDataItem.py a PC BACK (small subset of DRIVE_1_V3 with only two las files)
# AddRawDataItem.py a PC SITE
# AddRawDataItem.py a PIC
# AddRawDataItem.py a MESH
# UpdateDB.py
# GeneratePOTree.py
# GenerateOSG.py
# UpdateDB.py
# CreateOSGConfig.py
# CreatePotreeConfig.p

cleanup()


print "Scripts testing DONE!"
    