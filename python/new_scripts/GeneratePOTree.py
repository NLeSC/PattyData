#!/usr/bin/env python
################################################################################
#    Authors Romulo Goncalves and Oscar Martinez                               #
#    r.goncalves@esciencecenter.nl and o.rubi@esciencecenter.nl                #
################################################################################
import os, optparse, time, re, multiprocessing, glob, logging, shutil, subprocess
import utils 

# The data for VIAAPPIA must follow certain data structure.
# The DATA folder must have the structure defined in PattyData/Documents/storage/directory_structure.pdf
#(https://github.com/NLeSC/PattyData/blob/master/Documents/storage/directory_structure.pdf).
# The POTREE folder will then be populated using this script.

CONVERTER_COMMAND = 'PotreeConverter'
DEFAULT_SCENE_TYPE = 'bs'
DEFAULT_OUTPUT_FORMAT = 'LAS'
LOG_LEVELS = ('DEBUG','INFO','WARNING','ERROR')
DEFAULT_LOG_LEVEL = LOG_LEVELS[0]

# Get time when we start the update process
initialTime = utils.getCurrentTime()
#Declare variable for global connection to DB
connection = None

def main(opts):
    # Set logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y/%m/%d/%H:%M:%S", level=getattr(logging, opts.log))

    # Paths for the data
    rawAbsPath = os.path.abspath(opts.rawDir)
    potreeAbsPath = os.path.abspath(opts.potreeDir)

    pcAbsPath = os.path.join(rawAbsPath, utils.PC_FT)
    potreePCAbsPath = os.path.join(potreeAbsPath, utils.PC_FT)

    if 'b' in opts.sceneType:
    	backgroundAbsPath = os.path.join(pcAbsPath, utils.BG_FT)
	potreeBackgroundAbsPath = os.path.join(potreePCAbsPath, utils.BG_FT)
        processPCScene(backgroundAbsPath, potreeBackgroundAbsPath, opts.outputFormat, opts.levels)
    if 's' in opts.sceneType:
    	siteAbsPath = os.path.join(pcAbsPath, SITE_FT)
    	potreeSiteAbsPath = os.path.join(potreePCAbsPath, SITE_FT)
        processPCScene(siteAbsPath, potreeSiteAbsPath, opts.outputFormat, opts.levels)

    os.system('touch ' + os.path.join(potreeAbsPath, 'LAST_MOD'))

def processPCScene(inAbsPath, outAbsPath, outputFormat, levels):
    t0 = time.time()
    outName = os.path.basename(outAbsPath);
    logging.info('Running PotreeConverter for ' + outName)
    createPOTREE(outName, inAbsPath, outAbsPath, outputFormat, levels)

    logging.info('PotreeConverter processing finished in %.2f' % (time.time() - t0))


def createPOTREE(outName, inFile, outFolder, outputFormat, levels):
    if os.path.exists(outFolder):
        os.system('rm -rf ' + outFolder) 
    os.makedirs(outFolder)
    
    os.chdir(os.path.dirname(inFile))
    
    command = CONVERTER_COMMAND + ' -o ' + outFolder + ' -l ' + numLevels + ' --output-format ' + outputFormat + ' --source ' + inFile
    logFile = os.path.join(outFolder, outName + '.log')
    command += ' &> ' + logFile

    logging.info(command)
    #os.system(command)
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell = True).communicate()
   
    #TODO: Check if the number of files in data is equal to the number of nodes of the tree
    #grep "\"r" cloud.js | wc -l == ls data/ | wc -l

if __name__ == "__main__":
    usage = 'Usage: %prog [options]'
    description = "Creates the POTREE data for all the new data contained in the DATA/RAW folder and updates DB with information (it checks time stamps)"
    op = optparse.OptionParser(usage=usage, description=description)
    op.add_option('-i','--rawDir',default=utils.DEFAULT_RAW_DATA_FOLDER,help='RAW data folder [default ' + utils.DEFAULT_RAW_DATA_FOLDER + ']',type='string')
    op.add_option('-o','--potreeDir',default=utils.DEFAULT_POTREE_DATA_DIR,help='POTREE data directory [default ' + utils.DEFAULT_POTREE_DATA_DIR + ']',type='string')
    op.add_option('-s','--sceneType',default=DEFAULT_SCENE_TYPE,help='Type of Scene to be updated? b for background, s for sites [default all is checked, i.e. ' + DEFAULT_SCENE_TYPE + ']',type='string')
    op.add_option('-l','--levels',default='',help='Number of levels of the Octree, parameter for PotreeConverter.',type='string')
    op.add_option('-f','--outputFormat',default=DEFAULT_OUTPUT_FORMAT,help='Output format? LAS or LAZ [default '+ DEFAULT_OUTPUT_FORMAT + ']', type='string')
    op.add_option('-L','--log',help='Logging level (choose from ' + ','.join(LOG_LEVELS) + ' ; default ' + DEFAULT_LOG_LEVEL + ')',type='choice', choices=LOG_LEVELS, default=DEFAULT_LOG_LEVEL)
    (opts, args) = op.parse_args()
    main(opts)
