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


def createPOTree(opts, abOffsetX=None,
              abOffsetY=None, abOffsetZ=None, color8Bit=False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))

    # database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)
    # extract abspath using raw_data_item_id
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT abs_path, item_id FROM RAW_DATA_ITEM WHERE " +
        "raw_data_item_id = '%s'" % (opts.itemid))
    abspath, site_id = data_items[0]

    # extract inType & outFolder, create outFolder in non-existent
    inType, inKind, outFolder = extract_inType(abspath, site_id,
                                               opts.potreeDir)
    inFile = abspath  # CORRECT ?

    # Get 8bitcolor information from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT RAW_DATA_ITEM_PC.color_8bit, ' +
        'RAW_DATA_ITEM_MESH.color_8bit FROM RAW_DATA_ITEM LEFT JOIN ' +
        'RAW_DATA_ITEM_PC ON RAW_DATA_ITEM.raw_data_item_id=' +
        'RAW_DATA_ITEM_PC.raw_data_item_id LEFT JOIN RAW_DATA_ITEM_MESH ON ' +
        'RAW_DATA_ITEM.raw_data_item_id=RAW_DATA_ITEM_MESH.raw_data_item_id ' +
        'WHERE ' +
        'RAW_DATA_ITEM.raw_data_item_id = %s' % (opts.itemid))
    try:
        if (True in data_items[0]):
            color8Bit = True
        else:
            color8Bit = False
    except IndexError:
        color8Bit = False  # no 8BC color in database, set to false

    # Get alignment info from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT offset_x, offset_y, offset_z FROM ' +
        'OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM ON ' +
        'OSG_DATA_ITEM_PC_BACKGROUND.raw_data_item_id=' +
        'RAW_DATA_ITEM.raw_data_item_id WHERE RAW_DATA_ITEM.srid = ' +
        '(SELECT srid from RAW_DATA_ITEM WHERE raw_data_item_id=' +
        '%s )' % (opts.itemid))

    # Set offset if item is aligned
    if len(data_items) > 0:
        (abOffsetX, abOffsetY, abOffsetZ) = data_items[0]

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
    ofile = getOSGFileFormat(inType)

    # A PC SITE
    if (inType == utils.PC_FT and inKind == utils.SITE_FT):
        inputFiles = glob.glob(inFile + '/*.las') + glob.glob(
            inFile + '/*.laz')  # needed?
        # TODO: process item
    # A PC BACKGROUND
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):  # A PC BG
        inputFiles = glob.glob(inFile + '/*.las') + glob.glob(
            inFile + '/*.laz')  # needed?
        # TODO: process item        
    else:
        logger.error("POTree converter should one be used on PC's")
        raise Exception("POTree converter should one be used on PC's")

    logFile = os.path.join(outFolder, outputPrefix + '.log')
    
    # Call CONVERTER_COMMAND for each of the inputFiles
    for filename in inputFiles:
        command = CONVERTER_COMMAND + ' -o ' + outFolder + ' -l ' + \
            numLevels + ' --output-format ' + outputFormat + ' --source ' + \
                inFile
        if color8Bit:
            command += ' --8bitColor '
        if aligned:
            command += ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + \
                ' ' + str(abOffsetZ)
        command += ' &> ' + logFile
        logger.info(command)
        args = shlex.split(command)
        subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE).communicate()

    # move files to outFolder; drop outputPrefix from filename
#    outputFiles = glob.glob(outputPrefix + '*')
#    for filename in outputFiles:
#        if (inType == utils.PC_FT):
#            shutil.move(os.path.abspath(filename),
#                        os.path.join(outFolder,
#                                     filename[len(outputPrefix)+1:]))
#        else:
#            # outputPrefix is appended slightly different for PC and MESH
#            shutil.move(os.path.abspath(filename),
#                        os.path.join(outFolder,
#                                     filename[len(outputPrefix):]))

#    logger.info("Moving files to " + outFolder)

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*' + ofile)))
    if len(ofiles) == 0:
        logger.error('none POTree file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile)
        raise Exception('none POTree file was generated (found in ' + outFolder +
                        '). Check log: ' + logFile)
#    else:
#        pass


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
                                 os.path.basename(os.path.normpath(abspath)))
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):
        outFolder = os.path.join(os.path.abspath(potreeDir), utils.PC_FT,
                                 inKind,
                                 os.path.basename(os.path.normpath(abspath)))
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
    logger.info('Starting script GenerateOSG.py')
    logger.info('#######################################')
    createPOTree(opts)

if __name__ == "__main__":
    # define argument menu
    description = "Updates DB from the changes in the XML configuration file"
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i', '--itemid', help='Raw data item id',
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
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
