#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#            and Elena Ranguelova                                              #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
#import os, argparse, psycopg2, time, re, multiprocessing, glob, logging, shutil, subprocess
import os, argparse, time, glob, json. logging
import utils 

# The DATA folder must have the following structure:
#
# DATA
# |- BACKGROUND
# |  |- RAW
#        |- pc1
#            |- data
#            |- pc1.json EXAMPLE: {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0], "t_x" : None, ...}
#        |- pc2
# ...
# |  \- CONV
#        |- pc1
#            |- pc1v1
#               |- data
#               |- pc1v1.js
#            |- pc1v2
#            ...
#        |- pc2
# ...
# \- SITES
#     |-  1
#     ... |-PIC
#         |  |- CURR
#         |  \- HIST
#         |- MESHES     
#         |  |- CURR
#         |  \- ARCH_RECONS
#         |- PC     
#         |  |- RAW
#         |  |    |- pc1
#         |  |        |- pc1.json EXAMPLE: {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0], "t_x" : None, ...}
#         |  |        \- pc1.las
#         |  |    |- pc2
#         |  |    ...
#         |  \- CONV
#         |      |- pc1
#         |          |- pc1v1
#         |             |- data
#         |             |- pc1v1.js
#         |          |- pc1v2
#         |          ...
#         |      |- pc2

# CONSTANTS
LOG_LEVELS = ['DEBUG','INFO','WARNING','ERROR']
DEFAULT_LOG_LEVEL = LOG_LEVELS[0]
DEFAULT_DB = 'vadb'

# Global variables
cursor = None
dataAbsPath = None
# Get time when we start the update process
initialTime = utils.getCurrentTime()

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Run the script to populate the database")
    #formatter_class=argparse.RawTextHelpFormatter) 
    parser.add_argument('-i','--data',help='Input data folder',type=str, required=True)
    parser.add_argument('-d','--dbname',default=DEFAULT_DB,help='PostgreSQL DB name where to store the geometries [default ' + DEFAULT_DB + ']',type=str , required=True)
    parser.add_argument('-u','--dbuser',default=username,help='DB user [default ' + username + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=True)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=True)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=True)
    parser.add_argument('-l','--log',help='Logging level (choose from ' + ','.join(LOG_LEVELS) + ' ; default ' + DEFAULT_LOG_LEVEL + ')',type=str, choices=LOG_LEVELS, default=DEFAULT_LOG_LEVEL)
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

def processPC(pcAbsPath, tableName, siteId):
    rawPCAbsPath = os.path.join(pcAbsPath,'RAW')
    convPCAbsPath = os.path.join(pcAbsPath,'CONV')
    
    rawPCs = sorted(os.listdir(rawPCAbsPath))
    convPCs = sorted(os.listdir(convPCAbsPath))
    
    # Process the raw backgrounds         
    for rawPC in rawPCs:
        if rawPC not in convPCs:
            logging.warning(tableName + ' ' + rawPC + ' not found in ' + convPCAbsPath)
        processRawPC(rawPC, os.path.join(rawPCAbsPath, rawPC), tableName, siteId)
    
    # Process the converted backgrounds
    for convPC in convPCs:
        if convPC not in rawPCs:
            logging.error(tableName + ' ' + convPC + ' not found in ' + rawPCAbsPath)
        processConvertedPC(convPC, os.path.join(convPCsAbsPath, convPC), tableName)


def processRawPC(rawPCName, rawPCAbsPath, tableName, siteId = None):
    modTime = utils.getCurrentTime(utils.getLastModification(rawPCAbsPath))
    jsonFiles = glob.glob(os.path.join(rawPCAbsPath, '*json'))
    if len(jsonFiles) != 1:
        logging.error(rawPCAbsPath + ' does not contain JSON file!')
    else:
        jsonAbsPath = os.path.join(rawPCAbsPath,jsonFiles[0])
        jsonData = json.loads(open(jsonAbsPath,'r').read())
        utils.dbExecute(cursor, 'SELECT pc_id, last_mod FROM pc WHERE folder = %s', [rawPCAbsPath.replace(dataAbsPath,''),])
        row = cursor.fetchone()
        toAdd=True
        if row != None:
            (pcId, timeStamp) = row
            if modTime > timeStamp:
                utils.dbExecute(cursor, 'DELETE FROM pc WHERE pc_id = %s', [pcId,])
                utils.dbExecute(cursor, 'DELETE FROM ' + tableName + ' WHERE pc_id = %s', [pcId,])
            else:
                toAdd = False
        if toAdd: #This folder has been added recently
            (minx,miny,minz) = jsonData["min"]
            (maxx,maxy,maxz) = jsonData["max"]
            values = [jsonData["srid"],jsonData["numberpoints"],rawPCAbsPath.replace(dataAbsPath,''),jsonData["extension"],modTime,checkedTime,minx,miny,minz,maxx,maxy,maxz]
            utils.dbExecute(cursor, 'INSERT INTO pc (pc_id, srid, numberpoints, folder, extension, last_mod,last_check,minx,miny,minz,maxx,maxy,maxz) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING pc_id', values)
            (pcId,) = cursor.fetchone()
            names = ['name', 'pc_id']
            values = [rawPCName, pcId]
            if siteId == None:
                names.append('site_id')
                values.append(siteId)
                
            utils.dbExecute(cursor, 'INSERT INTO ' + tableName + ' (' + ','.join(names) + ') VALUES (' +  ('%s,' * len(values))[:-1] + ')', values)

def processConvertedPC(convPCName, convPCAbsPath, tableName):
    # Check that there is a related RAW PC
    utils.dbExecute(cursor, 'SELECT pc_id FROM ' + tableName + ' WHERE name = %s', [convPCName,])
    if cursor.rowcount != 1:
        logging.error('There are ' + str(cursor.rowcount) + ' ' + tableName + ' with name=' + convPCName)
    else:
        (pcId,) = cursor.fetchone()
        # List different possible versions
        convPCVersions = sorted(os.listdir(convPCAbsPath))
        for convPCVersion in convPCVersions:
            convPCVersionAbsPath = os.path.join(convPCAbsPath,convPCVersion)
            modTime = utils.getCurrentTime(utils.getLastModification(convPCAbsPath))
            #Check that data directory exists and it is not empty
            dataAbsPath = os.path.join(convPCVersionAbsPath, 'data')
            if os.path.isdir(dataAbsPath) and os.listdir(dataAbsPath) != []:
                jsFiles = glob.glob(os.path.join(convPCVersionAbsPath, '*js'))
                if len(jsFiles) == 1:
                    utils.dbExecute(cursor, 'SELECT pc_id, last_mod FROM pc_converted_file WHERE data_folder = %s', [dataAbsPath.replace(dataAbsPath,''),])
                    row = cursor.fetchone()
                    toAdd=True
                    if row != None:
                        (pcId, timeStamp) = row
                        if modTime > timeStamp:
                            utils.dbExecute(cursor, 'DELETE FROM pc_converted_file WHERE pc_id = %s', [pcId,])
                        else:
                            toAdd = False
                    if toAdd:
                        utils.dbExecute(cursor, 'INSERT INTO pc_converted_file (pc_id, data_folder, js_path) VALUES (%s,%s, %s)', [pcId, dataAbsPath.replace(dataAbsPath,''), os.path.join(convPCVersionAbsPath, jsFiles[0]).replace(dataAbsPath,'')])
                else:
                    logging.error('There are ' + str(len(jsFiles)) + ' JS files in ' + convPCVersionAbsPath)
            else:
                logging.error(dataAbsPath + ' does not exist')
def run(args):    
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, args.log))
    t0 = time.time()
    # Global variables declaration
    global cursor
    global dataAbsPath
    global checkedTime
    
    # Absolute data path
    dataAbsPath = os.path.abspath(args.data)  
    
    # Start DB connection
    connection = psycopg2.connect(utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, False))
    cursor = connection.cursor()
    
    checkedTime = utils.getCurrentTime()
    
    
    # Process the backgrounds
    backgroundsAbsPath = os.path.join(dataAbsPath,'BACKGROUND')
    processPC(backgroundsAbsPath, 'background')
        
    #Process sites
    sitesAbsPath = os.path.join(dataAbsPath,'SITES')
    sites = sorted(os.listdir(sitesAbsPath))
    for site in sites:
        siteId = int(site)
        utils.dbExecute(cursor, 'SELECT * FROM site where site_id = %s', [siteId], )
        if cursor.rowcount == 0:
            logging.warning('Site ' + site + ' not found in site table. Inserting it with NULL name and geom')
            utils.dbExecute(cursor, 'INSERT INTO site (site_id) VALUES (%s)', [siteId], )
        # Process the PCs
        processPC(os.path.join(sitesAbsPath,'PC'), 'site_pc', siteId)
        # TODO: Process the PICs and MESHEs
            
    # Clean removed pcs
    utils.dbExecute(cursor, 'DELETE FROM pc_converted_file WHERE last_check < %s', [initialTime,])
    utils.dbExecute(cursor, 'SELECT pc_id,folder FROM pc WHERE last_check < %s', [initialTime,])
    rows = cursor.fetchall()
    for (pcId,folder) in rows:
        utils.dbExecute(cursor, 'DELETE FROM site_pc WHERE pc_id = %s', [pcId,])    
        utils.dbExecute(cursor, 'DELETE FROM background WHERE pc_id = %s', [pcId,])
        deletePC = True
        utils.dbExecute(cursor, 'SELECT data_folder FROM pc_converted_file WHERE pc_id = %s', [pcId,])
        if cursor.rowcount != 0:
            logging.error("We can not delete PC row in " + folder + '. There are ' + str(cursor.rowcount) + ' related pc_converted_file')
            deletePC = False
        utils.dbExecute(cursor, 'SELECT data_folder FROM pc_converted_table WHERE pc_id = %s', [pcId,])
        if cursor.rowcount != 0:
            logging.error("We can not delete PC row in " + folder + '. There are ' + str(cursor.rowcount) + ' related pc_converted_table')
            deletePC = False
        if deletePC:
             utils.dbExecute(cursor, 'DELETE FROM pc WHERE pc_id = %s', [pcId,])
             
    #TODO: Remove old PICs and MESHEs
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == '__main__':
    run( apply_argument_parser() )
