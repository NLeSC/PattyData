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

import shutil, time, os, utils, glob, subprocess, argparse, shlex, logging

CONVERTER_COMMAND = 'PotreeConverter'
outputFormat = 'LAS'

def createPOTree(cursor, itemId, potreeDir, levels):
    
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))

    # extract abspath using raw_data_item_id
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT abs_path, item_id FROM RAW_DATA_ITEM WHERE " +
        "raw_data_item_id = %s", (itemId,))
    abspath, site_id = data_items[0]

    # extract inType & outFolder, create outFolder in non-existent
    inType, inKind, outFolder = extract_inType(abspath, site_id,
                                               potreeDir, levels)
    inFile = abspath

    if os.path.isfile(inFile):
        # input was a file -> raise IOError
        error('Database key abspath should define a directory, ' +
                      'file detected: ' + inFile, outFolder)
        # os.chdir(os.path.dirname(inFile))
    else:
        # input is already a directory
        os.chdir(inFile)

    outputPrefix = 'data'

    logFile = os.path.join(outFolder, outputPrefix + '.log')
    
    command = CONVERTER_COMMAND + ' -o ' + outFolder + ' -l ' + \
        str(levels) + ' --output-format ' + outputFormat + ' --source ' + \
            inFile
    command += ' &> ' + logFile
    logging.info(command)
    args = shlex.split(command)
    subprocess.Popen(args, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE).communicate()

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*')))
    if len(ofiles) == 0:
        error('none POTree file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile, outFolder)

def extract_inType(abspath, site_id, potreeDir, levels):
    '''
    Checks the type of the input file using the file location
    '''
    if any(substring in abspath for substring in ['/PC/']):
        inType = utils.PC_FT
    else:
        logging.error("POTree converter should one be used on PC's")
        raise Exception("POTree converter should one be used on PC's")
    
    if '/SITE/' in abspath:
        inKind = utils.SITE_FT
    elif '/BACK/' in abspath:
        inKind = utils.BG_FT
    else:
        logging.error('could not determine kind from abspath')
        raise Exception('Could not determine kind from abspath')
    
    # define outFolder from potreeDir and inType
    if (inType == utils.PC_FT and inKind == utils.SITE_FT):
        outFolder = os.path.join(os.path.abspath(potreeDir), utils.PC_FT,
                                 inKind, 'S'+str(site_id),
                                 os.path.basename(os.path.normpath(abspath)),
                                 os.path.basename(os.path.normpath(abspath)) +
                                 '_levels_' + str(levels))
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):
        outFolder = os.path.join(os.path.abspath(potreeDir), utils.PC_FT,
                                 inKind,
                                 os.path.basename(os.path.normpath(abspath)),
                                 os.path.basename(os.path.normpath(abspath)) +
                                 '_levels_' + str(levels))
    else:
        logging.error("POTree converter should one be used on PC's")
        raise Exception("POTree converter should one be used on PC's")
        
    # create outFolder if it does not exist yet
    if not os.path.isdir(outFolder):
        os.makedirs(outFolder)
    else:
        raise IOError('Output folder ' + outFolder + ' already exists, ' +
                      'please remove manually')
        # shutil.rmtree(outFolder)  # if we won't to force remove it
    return inType, inKind, outFolder

def error(errorMessage, outFolder):
     logging.error(errorMessage)
     logging.info('Removing %s ' % outFolder)
     shutil.rmtree(outFolder)
     raise Exception(errorMessage)

def getNumLevels(opts, isBackground):
    if opts.levels == '':
        if isBackground:
            levels = 8
        else:
            levels = 4
    else:
        levels = int(opts.levels)
    return levels

def main(opts):
    # Start logging
    logname = os.path.basename(__file__).split('.')[0] + '.log'
    utils.start_logging(filename=logname, level=opts.log)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logging.info(msg)
    # database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)
    
    if opts.itemid == '?':
        utils.listRawDataItems(cursor)
        return
    elif opts.itemid == '' or opts.itemid == '!':
        query = """
SELECT raw_data_item_id,abs_path,background 
FROM RAW_DATA_ITEM JOIN ITEM USING (item_id) JOIN RAW_DATA_ITEM_PC USING (raw_data_item_id) 
WHERE raw_data_item_id NOT IN (
          SELECT raw_data_item_id FROM POTREE_DATA_ITEM_PC)"""
        # Get the list of items that are not converted yet (we sort by background to have the background converted first)
        raw_data_items, num_raw_data_items = utils.fetchDataFromDB(cursor, query)
        for (rawDataItemId,absPath,isBackground) in raw_data_items:
            if opts.itemid == '' :
                levels = getNumLevels(opts, isBackground)
                createPOTree(cursor, rawDataItemId, opts.potreeDir, levels)
            else:
                m = '\t'.join((str(rawDataItemId),absPath))
                print m
                logging.info(m)
                
    else:
        for rawDataItemId in opts.itemid.split(','):
            rows,num_rows = utils.fetchDataFromDB(cursor, 'SELECT background FROM RAW_DATA_ITEM JOIN ITEM USING (item_id) WHERE raw_data_item_id = %s', [int(rawDataItemId)])
            if num_rows == 0:
                logging.error('There is not a raw data item with id %d' % int(rawDataItemId))
                return
            isBackground = rows[0][0]
            levels = getNumLevels(opts, isBackground)    
            createPOTree(cursor, int(rawDataItemId), opts.potreeDir, levels)

    # close DB connection
    utils.closeConnectionDB(connection, cursor)

    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logging.info(msg)

if __name__ == "__main__":
    # define argument menu
    description = "Generates the POTree data for a raw data item (ONLY FOR PCs)"
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i','--itemid',default='',
                       help='Comma-separated list of PointCloud Raw Data Item Ids [default is to convert all raw data items that do not have a related POtree data item] (with ? the available raw data items are listed, with ! the list all the raw data items without any related POTree data item)',
                       type=str, required=False)
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
    parser.add_argument('--levels',default='',help='Number of levels of the Octree, parameter for PotreeConverter. [default is 4 for Sites and 8 for Backgrounds]',action='store', required=False)
    
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
