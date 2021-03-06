# import general modules
from ConfigParser import ConfigParser
import os, sys, shutil, errno

# import the tested modules
testFolder = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir))
currentFolder = os.getcwd()
scriptsFolder = os.path.abspath(os.path.join(testFolder, '../python'))
sys.path.append(scriptsFolder)

import utils
import CreateDB, UpdateDBFootprints, UpdateDBAttribute, UpdateDBItemZ, UpdateDB
import AddRawDataItem, GeneratePOTree, GenerateOSG
import CreateOSGConfig, CreatePOTreeConfig

# checking log filefor errors
def checkLogFile(logFile, scriptName):
    if os.path.isfile(logFile):
        open(logFile,'r').read()
        if logFile.count('ERROR') > 0:
            print 'ERRORs in %s. See %s' %(scriptName,logFile)
            cleanup_data()
            cleanup_db()
            sys.exit()
    else:
        print 'Could not open the %s logfile' %logFile    
        
# get configuration from an ini file 
def getConfig(testFolder, iniFileName):
    """ Gets configuraiton handle from an ini file """
    config = ConfigParser()
    config.optionxform=str
    config.read(os.path.abspath(os.path.join(testFolder, iniFileName )))
    
    return config

def cleanup_data():
# clean everything
    print "Cleaning up..."
# cleanup the local test data directory structure 
    if os.path.exists(dataPath):
       shutil.rmtree(dataPath)
    if os.path.exists(PotreePath):
       shutil.rmtree(PotreePath)       
       
    files = os.listdir(currentFolder)
    for f in files:
        if os.path.isfile(f) & f.endswith('.log'):
            print "Cleaned up log file: ", f
            os.remove(f)
    print "If existing:"
    print "Log files have been removed." 
    print "DATA folder has been removed."
    print "PC (Potree) folder has been removed."
    
    print "Cleaning up...DONE"
    print "-----------------------------------------------------------------------"
    
def cleanup_db():
# drop the test DB
    os.system('dropdb ' + utils.postgresConnectString(dbName, dbUser, dbPass, dbHost, dbPort, True))   
    print "Test DB has been dropped."
    
def fillTestData(localDataPath, serverDataPath):
    """ copies some test data from the server data path to the local data path"""
    print "Copying test data locally ..."
    fillOSGData(localDataPath, serverDataPath)
    fillRAWData(localDataPath, serverDataPath)
    fillPOTREEData(localDataPath, serverDataPath)
    print "Copying test data locally ... DONE"
    print "-----------------------------------------------------------------------"  
    
def fillPOTREEData(localDataPath, serverDataPath):    
    """ copies some POTREE test data from the server data path to the local data path"""
    
    POTREELocalDataPath = os.path.join(localDataPath, 'POTREE')
    POTREEServerDataPath =os.path.join(serverDataPath, 'POTREE')
    
    fillPcData(POTREELocalDataPath, POTREEServerDataPath)
    
def fillOSGData(localDataPath, serverDataPath):    
    """ copies some OSG test data from the server data path to the local data path"""
    
    OSGLocalDataPath = os.path.join(localDataPath, 'OSG')
    OSGServerDataPath =os.path.join(serverDataPath, 'OSG')
    
    fillPcData(OSGLocalDataPath, OSGServerDataPath)
    fillMeshData(OSGLocalDataPath, OSGServerDataPath)
    fillPictData(OSGLocalDataPath, OSGServerDataPath)

def fillRAWData(localDataPath, serverDataPath):    
    """ copies some RAW test data from the server data path to the local data path"""
    
    RAWLocalDataPath = os.path.join(localDataPath, 'RAW')
    RAWServerDataPath =os.path.join(serverDataPath, 'RAW')
    
    fillPcData(RAWLocalDataPath, RAWServerDataPath)
    fillMeshData(RAWLocalDataPath, RAWServerDataPath)
    fillPictData(RAWLocalDataPath, RAWServerDataPath)
    
def fillPcData(LocalDataPath, ServerDataPath):    
    """ copies some PC test data from the server data path to the local data path"""
    # set up some paths shortcuts
    
    PCLocalDataPath = os.path.join(LocalDataPath, 'PC')
    PCServerDataPath = os.path.join(ServerDataPath, 'PC')
    SitePCLocalDataPath = os.path.join(PCLocalDataPath, 'SITE')
    SitePCServerDataPath = os.path.join(PCServerDataPath, 'SITE')
    BGPCLocalDataPath = os.path.join(PCLocalDataPath, 'BACK')
    BGPCServerDataPath = os.path.join(PCServerDataPath, 'BACK')
    
    
    # copy data    
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
        
  
##############################################################################
### Setup ###

# get configuration handle
print "-----------------------------------------------------------------------"
print "-------------Testing of the python scripts in PattyData----------------"
print "-----------------------------------------------------------------------"

print " Setting up..."
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
PotreePath = config.get('Data','PotreePath')
serverDataPath = config.get('Data','ServerPath')

# define test arguments class
class testArguments:
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)
        
print "Test arguments class defined."        
print "Scripts input parameters loaded."    
print " Setting up...DONE."  
print "-----------------------------------------------------------------------"

##############################################################################
cleanup_data()
cleanup_db()

if not os.path.exists(dataPath):
    fillTestData(dataPath, serverDataPath)

# create test  DB
print " Testing creation of the DB ..."
sqlFile = os.path.abspath(os.path.join(testFolder, '../Database/ERDB.sql'))

DBargs = testArguments(sql=sqlFile, dbname=dbName, dbuser = dbUser, \
                dbpass =dbPass, dbhost = dbHost, dbport = dbPort, log=logLevel)
CreateDB.run(DBargs)

logFile = os.path.basename(sqlFile)  + '.log'
scriptName =  'CreateDB.py'
scriptName = 'UpdateDBItemZ.py'
checkLogFile(logFile, scriptName)
        
print " The testing of the creation of the DB...DONE."
print "-----------------------------------------------------------------------"

#if True:
# update the footprints
print " Testing updating the DB with the sites' footprints... "

footprArgs = testArguments(input = footprints_file, dbname=dbName, dbuser=dbUser,\
                            dbpass=dbPass, dbhost=dbHost, dbport=dbPort)
UpdateDBFootprints.run(footprArgs)

logFile = os.path.basename(footprints_file) + '.log'
scriptName = 'UpdateFootprints.py'
checkLogFile(logFile, scriptName)   

        
print "The testing of the footprints DB update...DONE."
print "-----------------------------------------------------------------------"

# update the attributes
print " Testing updating the Attributes in the DB... "

attrArgs = testArguments(input = attributes_file, dbname=dbName, dbuser=dbUser,\
                            dbpass=dbPass, dbhost=dbHost, dbport=dbPort, log =logLevel)
UpdateDBAttribute.run(attrArgs)

logFile = os.path.basename(attributes_file) + '.log'
checkLogFile(logFile, 'UpdateDBAttribute.py')
        
print " The testing of the attributes DB update...DONE."
print "-----------------------------------------------------------------------"

# update the Z of some sites
print " Testing updating the Z of given items in the DB... "

ZArgs = testArguments(itemid=footprints_item_ids, las= footprints_drive_map,\
                     dbname= dbName, dbuser=dbUser, dbpass= dbPass,\
                     dbhost=dbHost, dbport= dbPort, cores= 16)
UpdateDBItemZ.run(ZArgs)

logFile = 'UpdateDBItemZ.log'
scriptName = 'UpdateDBItemZ.py'
checkLogFile(logFile, scriptName)
        
print " The testing of the updating the Z of given items in the DB...DONE."
print "-----------------------------------------------------------------------"
   

print " Testing adding raw data items..."

# AddRawDataItem.py a PC BACK (small subset of DRIVE_1_V3 with only two las files)
print "Adding BG PC data ..."
PCBGArgs=testArguments(data=os.path.join(dataPath,'RAW'), kind=utils.BG_FT, \
                        type=utils.PC_FT, \
                        file="/home/pattydat/DATA/RAW/PC/BACK/DRIVE_1_V4", \
                        log=logLevel, eight=False, srid='')
AddRawDataItem.run(PCBGArgs)
print "Adding BG PC data ...DONE"

# AddRawDataItem.py a PC SITE
print "Adding SITE PC data ..."
PCSiteArgs=testArguments(data=os.path.join(dataPath,'RAW'), kind=utils.SITE_FT, \
                        type=utils.PC_FT, \
                        file="/home/pattydat/DATA/RAW/PC/SITE/S1/" +
                        "SITE_1_O_1_VSFM_CLEANED_aligned_DRIVE_1_V3/" +
                        "SITE_1_O_1_VSFM_CLEANED_aligned_DRIVE_1_V3.las", \
                        log=logLevel, eight=False, srid='', site = '1')
AddRawDataItem.run(PCSiteArgs)
print "Adding SITE PC data ...DONE"

# AddRawDataItem.py a PICT
print "Adding PICT SITE data ..."
PictArgs=testArguments(data=os.path.join(dataPath,'RAW'), kind=utils.SITE_FT,\
                        type=utils.PIC_FT, period = utils.CURR_FT, \
                        file="/home/pattydat/DATA/RAW/PICT/SITE/CURR/S42/" +
                        "SITE_42_O_A_126/SITE_42_O_A_126.JPG", \
                        log=logLevel, eight=False, srid='', site = '42')
AddRawDataItem.run(PictArgs)
print "Adding PICT SITE data ...DONE"

#AddRawDataItem.py a MESH
print "Adding MESH SITE data ..."
MeshArgs=testArguments(data=os.path.join(dataPath,'RAW'), kind=utils.SITE_FT, \
                        type=utils.MESH_FT, period = utils.CURR_FT,\
                        file="/home/pattydat/DATA/RAW/MESH/SITE/CURR/S20" +
                        "/SITE_20_O_1_VSFM_TEXTURE", \
                        log=logLevel, eight=False, srid='33333', site = '20')
AddRawDataItem.run(MeshArgs)
print "Adding MESH SITE data ...DONE"

logFile = 'AddRawDataItem.log'
scriptName = 'AddRawDataItem.py'
checkLogFile(logFile, scriptName)

print " Testing adding raw data items...DONE"
print "-----------------------------------------------------------------------"


# UpdateDB.py
print " Testing updating the DB... "
UpdateDBArgs = testArguments(data=dataPath, types='rop', ditypes='pmi',\
                  dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                  dbhost=dbHost, dbport=dbPort, log=logLevel)

UpdateDB.run(UpdateDBArgs)

logFile = 'UpdateDB.log'
scriptName = 'UpdateDB.py'
checkLogFile(logFile, scriptName)
        
print " The testing of the updating the DB...DONE."
print "-----------------------------------------------------------------------"


# GeneratePOTree.py
print " Testing generating POTree... "
PotreeArgs = testArguments(itemid='', potreeDir='',levels=4, \
                  dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                  dbhost=dbHost, dbport=dbPort, log=logLevel)

GeneratePOTree.run(PotreeArgs)

logFile = 'GeneratePOTree.log'
scriptName = 'GeneratePOTree.py'
checkLogFile(logFile, scriptName)

print " The testing of generating the POTree...DONE."
print "-----------------------------------------------------------------------"

# GenerateOSG.py
print " Testing generating OSG... "
OSGArgs = testArguments(itemid='', osgDir='',\
                  dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                  dbhost=dbHost, dbport=dbPort, log=logLevel)

GenerateOSG.run(OSGArgs)
os.system('pwd')
logFile = 'GenerateOSG.log'
scriptName = 'GenerateOSG.py'
checkLogFile(logFile, scriptName)


print " The testing of generating the OSG...DONE."
print "-----------------------------------------------------------------------"
    
# UpdateDB.py
print " Testing again updating the DB... "
UpdateDBArgs = testArguments(data=dataPath, types='rop', ditypes='pmi',\
                  dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                  dbhost=dbHost, dbport=dbPort, log=logLevel)

UpdateDB.run(UpdateDBArgs)

logFile = 'UpdateDB.log'
scriptName = 'UpdateDB.py'
checkLogFile(logFile, scriptName)

print " The second testing of the updating the DB...DONE."
print "-----------------------------------------------------------------------"

# CreateOSGConfig.py
print " Testing creating of OSG configuration... "
OSGConfigArgs = testArguments(output='TestOSG.conf.xml', \
                                osg=os.path.join(dataPath,'OSG'),\
                                background='DRIVE_1_V3',\
                                dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                                dbhost=dbHost, dbport=dbPort, log=logLevel)

CreateOSGConfig.run(OSGConfigArgs)

logFile = 'CreateOSGConfig.log'
scriptName = 'CreateOSGConfig.py'
checkLogFile(logFile, scriptName)

print " The testing of creating the OSG configuration...DONE."
print "-----------------------------------------------------------------------"
    

# CreatePotreeConfig.py
print " Testing creating of POTree configuration... "
POTreeConfigArgs = testArguments(output='TestPOTREE.json', \
                                srid = 55555,\
                                dbname=dbName, dbuser=dbUser, dbpass=dbPass,\
                                dbhost=dbHost, dbport=dbPort, log=logLevel)

CreatePOTreeConfig.run(POTreeConfigArgs)

logFile = 'CreatePOTreeConfig.log'
scriptName = 'CreatePOTreeConfig.py'
checkLogFile(logFile, scriptName)
        
print " The testing of creating the POTree configuration...DONE."
print "-----------------------------------------------------------------------"

cleanup_db()
cleanup_data()


print "Scripts testing DONE!"
    