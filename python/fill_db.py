#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#            and Elena Ranguelova                                              #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
#import os, argparse, psycopg2, time, re, multiprocessing, glob, logging, shutil, subprocess
import os, argparse, time, glob
import utils 

# The DATA folder must have the following structure:
#
# DATA
# |- BACKGROUND
# |  |- RAW
#        |- pc1
#            |- data
#            |- pc1.json EXAMPLE: {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}
#        |- pc2
# ...
# |  \- CONV
#        |- pc1
#            |- pc1v1
#               |- data
#               |- pc1v1.js EXAMPLE: {"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}
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
#         |  \- CONV
#                 |- pc1
#                 |- pc2
#                 ...

# CONSTANTS
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
    t0 = time.time()
    # Check options
        
    # Absolute data path
    dataAbsPath = os.path.abspath(args.data)
    
    # Global variables declaration
    global connection
    
    # Start DB connection
    #connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    #cursor = connection.cursor()
    
    # Process the backgrounds
    backgroundsAbsPath = os.path.join(dataAbsPath,'BACKGROUND')
    rawBackgroundsAbsPath = os.path.join(backgroundsAbsPath,'RAW')
    convBackgroundsAbsPath = os.path.join(backgroundsAbsPath,'CONV')
    
    rawBackgrounds = sorted(os.listdir(rawBackgroundsAbsPath))
    convBackgrounds = sorted(os.listdir(convBackgroundsAbsPath))
    
    for rawBackground in rawBackgrounds:
        if rawBackground not in convBackgrounds:
            print 'ERROR: background ' + rawBackground + ' not found in ' + convBackgroundsAbsPath
        rawBackgroundAbsPath = os.path.join(rawBackgroundsAbsPath,rawBackground)
        glob.glob()
    
    
    #{"srid": 32633, "max": [0, 0, 0], "numberpoints": 20000000, "extension": "laz", "min": [0, 0, 0]}
    
    #for background in backgrounds:
    #    backgroundAbsPath = os.path.join(backgroundsAbsPath, background)
        
    
    
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == '__main__':
    run( apply_argument_parser() )