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
connection = None

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

def run(args):    
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, args.log))
    t0 = time.time()
    # Check options
        
    # Absolute data path
    dataAbsPath = os.path.abspath(args.data)
    
    # Global variables declaration
    global connection
    
    # Start DB connection
    connection = psycopg2.connect(utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, False))
    cursor = connection.cursor()
    
    # Process the backgrounds
    backgroundsAbsPath = os.path.join(dataAbsPath,'BACKGROUND')
    rawBackgroundsAbsPath = os.path.join(backgroundsAbsPath,'RAW')
    convBackgroundsAbsPath = os.path.join(backgroundsAbsPath,'CONV')
    
    rawBackgrounds = sorted(os.listdir(rawBackgroundsAbsPath))
    convBackgrounds = sorted(os.listdir(convBackgroundsAbsPath))
    
    # Check that there are not backgrounds in converted which are not in raw
    for convBackground in convBackgrounds:
        if convBackground not in rawBackgrounds:
            logging.error('background ' + convBackground + ' not found in ' + rawBackgroundsAbsPath)
    
    checkedTime = utils.getCurrentTime()
    
    # Add         
    for rawBackground in rawBackgrounds:
        if rawBackground not in convBackgrounds:
            logging.warning('background ' + rawBackground + ' not found in ' + convBackgroundsAbsPath)
        rawBackgroundAbsPath = os.path.join(rawBackgroundsAbsPath, rawBackground)
        modTime = utils.getCurrentTime(utils.getLastModification(rawBackgroundAbsPath))
        jsonFiles = glob.glob(os.path.join(rawBackgroundAbsPath, '*json'))
        if len(jsonFiles) != 1:
            logging.error(' background ' + rawBackground + ' does not contain JSON file!')
        else:
            jsonAbsPath = os.path.join(rawBackgroundAbsPath,rawBackground)
            jsonData = json.loads(open(jsonFiles[0],'r').read())
            # {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}
            utils.dbExecute(cursor, 'SELECT pc_id, last_mod FROM pc WHERE folder = %s', [rawBackgroundAbsPath,])
            row = cursor.fetchone()
            toAdd=True
            if row != None:
                (pcId, timeStamp) = row
                if modTime > timeStamp:
                    # Data has changed, we re-create the OSG data
                    utils.dbExecute(cursor, 'DELETE FROM pc WHERE pc_id = %s', [pcId,])
                    utils.dbExecute(cursor, 'DELETE FROM background WHERE pc_id = %s', [pcId,])
                else:
                    toAdd = False
            if toAdd: #This folder has been added recently
                (minx,miny,minz) = jsonData["min"]
                (maxx,maxy,maxz) = jsonData["max"]
                values = [jsonData["srid"],jsonData["numberpoints"],rawBackgroundAbsPath.replace(dataAbsPath,''),jsonData["extension"],modTime,checkedTime,minx,miny,minz,maxx,maxy,maxz]
                utils.dbExecute(cursor, 'INSERT INTO pc (pc_id, srid, numberpoints, folder, extension, last_mod,last_check,minx,miny,minz,maxx,maxy,maxz) VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING pc_id', values)
                (pcId,) = cursor.fetchone()
                utils.dbExecute(cursor, 'INSERT INTO background (name, pc_id) VALUES (%s,%s)', [rawBackground, pcId])
                
    # Clean removed backgrounds
#     utils.dbExecute(cursor, 'DELETE FROM backgrounds_pc WHERE last_check < %s RETURNING static_object_id', [initialTime,])
#     rows = cursor.fetchall()
#     for (staticObjectId,) in rows:
#         utils.dbExecute(cursor, 'DELETE FROM static_objects WHERE static_object_id = %s RETURNING osg_path', [staticObjectId,])
#         osgPath = cursor.fetchone()[0]
#         shutil.rmtree(os.path.dirname(osgPath))  
    
    #{"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}
    
    #for background in backgrounds:
    #    backgroundAbsPath = os.path.join(backgroundsAbsPath, background)
        
    
    
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == '__main__':
    run( apply_argument_parser() )
