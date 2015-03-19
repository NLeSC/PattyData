from ConfigParser import ConfigParser
import os
from collections import namedtuple
import CreateDB

currentFolder = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir))

config = ConfigParser()
config.optionxform=str
config.read(os.path.abspath(os.path.join(currentFolder, 'test.ini')))

logLevel = config.get('General','LogLevel')

dbName = config.get('DB','Name')
dbHost = config.get('DB','Host')
dbUser = config.get('DB','User')
dbPass = config.get('DB','Pass')
dbPort = config.get('DB','Port')

dataAbsPath = os.path.abspath(config.get('Data','Path'))

sqlFile = os.path.abspath(os.path.join(currentFolder, '../Database/ERDB.sql'))
CreateDBArguements = namedtuple("Create DB Arguments", "sql dbname dbuser dbpass dbhost dbport log")
CreateDB.main(CreateDBArguements(sqlFile, dbName, dbUser, dbPass, dbHost, dbPort, logLevel))
logFile = sqlFile + '.log'
logFileContent = open(logFile,'r').read()
if logFile.count('ERROR') > 0:
    print 'ERRORs in CreateDB.py. See %s' % logFile

# Create dummy Data structure 


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
