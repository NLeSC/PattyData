#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
#import os, optparse, psycopg2, time, re, multiprocessing, glob, logging, shutil, subprocess
import os, optparse, time
import utils 

# The DATA folder must have the following structure:
#
# DATA
# |- BACKGROUND
# |  |- RAW
#        |- pc1
#        |- pc2
# ...
# |  \- CONV
#        |- pc1
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

def main(opts):
    t0 = time.time()
    # Check options
    for option in (opts.data, opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport):
        if option == '':
            print 'ERROR - missing options!'
            return
    
    # Absolute data path
    dataAbsPath = os.path.abspath(opts.data)
    
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
    
    
    
    #for background in backgrounds:
    #    backgroundAbsPath = os.path.join(backgroundsAbsPath, background)
        
    
    
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Fills the DB"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--data',help='Data folder',type='string', nargs='+')
    op.add_option('-d','--dbname',default=DEFAULT_DB,help='PostgreSQL DB name where to store the geometries [default ' + DEFAULT_DB + ']',type='string' , nargs='+')
    op.add_option('-u','--dbuser',default=username,help='DB user [default ' + username + ']',type='string', nargs='+')
    op.add_option('-p','--dbpass',default='',help='DB pass',type='string', nargs='+')
    op.add_option('-t','--dbhost',default='',help='DB host',type='string', nargs='+')
    op.add_option('-r','--dbport',default='',help='DB port',type='string', nargs='+')
    (opts, args) = op.parse_args()
    main(opts)
