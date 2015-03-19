# import general modules
from ConfigParser import ConfigParser
import os, sys, shutil
from collections import namedtuple
import itertools

# import the tested modules
currentFolder = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir))
scriptsFolder = os.path.abspath(os.path.join(currentFolder, '../python'))
sys.path.append(scriptsFolder)

import utils
import CreateDB


# get configuration from an ini file 
def getConfig(currentFolder, iniFileName):
    """ Gets configuraiton handle from an ini file """
    config = ConfigParser()
    config.optionxform=str
    config.read(os.path.abspath(os.path.join(currentFolder, iniFileName )))
    
    return config

##############################################################################
### Setup ###

# get configuration handle
print "-----------------------------------------------------------------------"
print "-------------Testing of the python scripts in PattyData----------------"
print "-----------------------------------------------------------------------"

print "Setting up..."
iniFileName = 'test.ini'

config = getConfig(currentFolder, iniFileName)

# read configuration parameters
logLevel = config.get('General','LogLevel')

dbName = config.get('DB','Name')
dbHost = config.get('DB','Host')
dbUser = config.get('DB','User')
dbPass = config.get('DB','Pass')
dbPort = config.get('DB','Port')

####
dataPath = config.get('Data','Path')
# clean everything
if os.path.exists(dataPath):
    shutil.rmtree(dataPath)
dirs = [[dataPath],
        ['RAW','OSG','POTREE'],
        ['PC','MESH','PICT','DOME','BOUND'],
        ['BACK', 'SITE'],
        ['CURR', 'HIST', 'ARCH_REC']]
# generate a redundant(very!) common directory structure
for item in itertools.product(*dirs):    
    os.makedirs(os.path.join(*item))
    
print "Directory structure (redundant) was created."  
print "Setting up...DONE."  
print "-----------------------------------------------------------------------"
##############################################################################

# create test  DB
print "Testing creation of the DB ..."
sqlFile = os.path.abspath(os.path.join(currentFolder, '../Database/ERDB.sql'))
CreateDBArguements = namedtuple("Create_DB_Arguments", "sql dbname dbuser dbpass dbhost dbport log")
CreateDB.run(CreateDBArguements(sqlFile, dbName, dbUser, dbPass, dbHost, dbPort, logLevel))
logFile = sqlFile + '.log'
logFileContent = open(logFile,'r').read()
if logFile.count('ERROR') > 0:
    print 'ERRORs in CreateDB.py. See %s' % logFile
print "The testing of the creation of the DB...DONE."
print "-----------------------------------------------------------------------"

# CreateDB.py -f ERDB.sql
# UpdateDBFootprints.py -i Footprints/20150306/VIA_APPIA_SITES_06032015.shp
# UpdateDBAttribute.py -i Attributes/20150312/VA2012-2014_12032015.mdb.sql
# UpdateDBItemZ.py -c 16 -l dataAbsPath
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
# CreatePotreeConfig.py

# clean everything
print "Cleaning up..."
# cleanup the data
if os.path.exists(dataPath):
    shutil.rmtree(dataPath)
# drop the test DB
os.system('dropdb ' + utils.postgresConnectString(dbName, dbUser, dbPass, dbHost, dbPort, True))
print "Cleaning up...DONE"
print "-----------------------------------------------------------------------"
print "DONE"
    