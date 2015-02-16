#!/usr/bin/env python
##############################################################################
# Description:      Script to convert raw data item using CONVERTER_COMMAND:
#                   POTree version
#
# Authors:          Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
#                   Romula Goncalves, NLeSC, r.goncalves@esciencecenter.nl
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
#
# Created:          11.02.2015
# Last modified:    11.02.2015
#
# Changes:
#
# Notes:            * User gives an ID from raw_data_item_id
#                   * From DB abspath is imported
#                   * Outfolder is defined
#                   * 8bitcolor and alignment info is queried from DB
#                   * Data is converted using CONVERTER_COMMAND
#                   * Unique identifier is created in xml config file
##############################################################################

import shutil
import os
import utils
import glob
import subprocess
import argparse
import shlex

logger = None

CONVERTER_COMMAND = 'PotreeConverter'
outputFormat = 'LAS'

def createPOTree(opts, abOffsetX=None,
              abOffsetY=None, abOffsetZ=None, color8Bit=False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))

    # database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)
    if opts.itemid == '?':
        utils.listRawDataItems(cursor)
        return
    
    # extract abspath using raw_data_item_id
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT abs_path, item_id FROM RAW_DATA_ITEM WHERE " +
        "raw_data_item_id = %s", (opts.itemid,))
    abspath, site_id = data_items[0]

    # extract inType & outFolder, create outFolder in non-existent
    inType, inKind, outFolder = extract_inType(abspath, site_id,
                                               opts.potreeDir)
    inFile = abspath

    # close DB connection
    utils.closeConnectionDB(connection, cursor)

    if os.path.isfile(inFile):
        # input was a file -> raise IOError
        raise IOERROR('Database key abspath should define a directory, ' +
                      'file detected: ' + inFile)
        # os.chdir(os.path.dirname(inFile))
    else:
        # input is already a directory
        os.chdir(inFile)

    outputPrefix = 'data'
    aligned = (abOffsetX is not None)

    logFile = os.path.join(outFolder, outputPrefix + '.log')
    
    command = CONVERTER_COMMAND + ' -o ' + outFolder + ' -l ' + \
        opts.levels + ' --output-format ' + outputFormat + ' --source ' + \
            inFile
    command += ' &> ' + logFile
    logger.info(command)
    args = shlex.split(command)
    subprocess.Popen(args, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE).communicate()

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*')))
    if len(ofiles) == 0:
        logger.error('none POTree file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile)
        raise Exception('none POTree file was generated (found in ' + outFolder +
                        '). Check log: ' + logFile)


def extract_inType(abspath, site_id, potreeDir):
    '''
    Checks the type of the input file using the file location
    '''
    if any(substring in abspath for substring in ['/PC/']):
        inType = utils.PC_FT
    else:
        logger.error("POTree converter should one be used on PC's")
        raise Exception("POTree converter should one be used on PC's")
    
    if '/SITE/' in abspath:
        inKind = utils.SITE_FT
    elif '/BACK/' in abspath:
        inKind = utils.BG_FT
    else:
        logger.error('could not determine kind from abspath')
        raise Exception('Could not determine kind from abspath')
    
    # define outFolder from potreeDir and inType
    if (inType == utils.PC_FT and inKind == utils.SITE_FT):
        outFolder = os.path.join(os.path.abspath(potreeDir), utils.PC_FT,
                                 inKind, 'S'+str(site_id),
                                 os.path.basename(os.path.normpath(abspath)),
                                 os.path.basename(os.path.normpath(abspath)) +
                                 '_levels_' + opts.levels)
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):
        outFolder = os.path.join(os.path.abspath(potreeDir), utils.PC_FT,
                                 inKind,
                                 os.path.basename(os.path.normpath(abspath)),
                                 os.path.basename(os.path.normpath(abspath)) +
                                 '_levels_' + opts.levels)
    else:
        logger.error("POTree converter should one be used on PC's")
        raise Exception("POTree converter should one be used on PC's")
        
    # create outFolder if it does not exist yet
    if not os.path.isdir(outFolder):
        os.makedirs(outFolder)
    else:
        raise IOError('Output folder ' + outFolder + ' already exists, ' +
                      'please remove manually')
        # shutil.rmtree(outFolder)  # if we won't to force remove it
    return inType, inKind, outFolder


def main(opts):
    # Define logger and start logging
    global logger
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script GeneratePOTree.py')
    logger.info('#######################################')
    createPOTree(opts)

if __name__ == "__main__":
    # define argument menu
    description = "Updates DB from the changes in the XML configuration file"
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i', '--itemid', help='Raw data item id (with ? the list of raw data items are listed)',
                        action='store', required=True)
    parser.add_argument('-d', '--dbname', default=utils.DEFAULT_DB,
                        help='Postgres DB name [default ' + utils.DEFAULT_DB +
                        ']', action='store')
    parser.add_argument('-u', '--dbuser', default=utils.USERNAME,
                        help='DB user [default ' + utils.USERNAME +
                        ']', action='store')
    parser.add_argument('-p', '--dbpass', help='DB pass', action='store')
    parser.add_argument('-t', '--dbhost', help='DB host', action='store')
    parser.add_argument('-r', '--dbport', help='DB port', action='store')
    parser.add_argument('-o', '--potreeDir', default=utils.DEFAULT_POTREE_DATA_DIR,
                        help='POTREE data directory [default ' +
                        utils.DEFAULT_POTREE_DATA_DIR + ']', action='store')
    parser.add_argument('--levels',default='',help='Number of levels of the Octree, parameter for PotreeConverter.',action='store', required=True)
    
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
