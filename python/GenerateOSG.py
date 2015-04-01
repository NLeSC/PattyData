#!/usr/bin/env python
##############################################################################
# Description:      Script to convert raw data item using CONVERTER_COMMAND
#
# Authors:          Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
#
# Created:          09.02.2015
# Last modified:    09.02.2015
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

import shutil, os, time, utils, glob, subprocess, argparse, shlex, logging

CONVERTER_COMMAND = 'ViaAppia'

cwd = None

def getOSGFileFormat(inType):
    return 'osgb'

def updateXMLDescription(xmlPath, cursor, aoType, rawDataItemId):
    # update description in xml file using unique identifier -> relative path
    tempFile = xmlPath + '_TEMP'
    ofile = open(tempFile, 'w')
    lines = open(xmlPath, 'r').readlines()
    uniqueName = utils.codeOSGActiveObjectUniqueName(cursor, aoType, rawDataItemId)
    for line in lines:
        if line.count('<description>'):
            ofile.write('    <description>' +
                        uniqueName + '</description>\n')
        else:
            ofile.write(line)
    os.remove(xmlPath)
    shutil.move(tempFile, xmlPath)


def createOSG(cursor, itemId, osgDir):
    global cwd
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))
    
    # extract abspath using raw_data_item_id
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT abs_path, item_id FROM RAW_DATA_ITEM WHERE " +
        "raw_data_item_id = %s", (itemId,))
    abspath, site_id = data_items[0]

    # extract inType & outFolder, create outFolder in non-existent
    inType, inKind, outFolder = extract_inType(abspath, site_id, osgDir)
    inFile = abspath  # CORRECT ?

    # Get 8bitcolor information from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT RAW_DATA_ITEM_PC.color_8bit, ' +
        'RAW_DATA_ITEM_MESH.color_8bit FROM RAW_DATA_ITEM LEFT JOIN ' +
        'RAW_DATA_ITEM_PC ON RAW_DATA_ITEM.raw_data_item_id=' +
        'RAW_DATA_ITEM_PC.raw_data_item_id LEFT JOIN RAW_DATA_ITEM_MESH ON ' +
        'RAW_DATA_ITEM.raw_data_item_id=RAW_DATA_ITEM_MESH.raw_data_item_id ' +
        'WHERE ' +
        'RAW_DATA_ITEM.raw_data_item_id = %s', (itemId,))
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
        '%s )', (itemId,))

    # Set offset if item is aligned
    aligned = False
    if len(data_items) > 0:
        aligned = True
        (abOffsetX, abOffsetY, abOffsetZ) = data_items[0]
    
    cwd = os.getcwd()
    if os.path.isfile(inFile):
        # input was a file -> raise IOError
        error('Database key abspath should define a directory, ' +
                      'file detected: ' + inFile, outFolder)
        # os.chdir(os.path.dirname(inFile))
    else:
        # input is already a directory
        os.chdir(inFile)

    outputPrefix = utils.OSG_DATA_PREFIX
    ofile = getOSGFileFormat(inType)

    # A PC SITE
    if (inType == utils.PC_FT and inKind == utils.SITE_FT):
        tmode = '--mode lodPoints --reposition'
        inputFiles = glob.glob(inFile + '/*.las') + glob.glob(
            inFile + '/*.laz')
    # A PC BACKGROUND
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):  # A PC BG
        tmode = '--mode quadtree --reposition'
        numLAS = len(glob.glob(inFile + '/*.las'))
        numLAZ = len(glob.glob(inFile + '/*.laz'))
        if (numLAS != 0) and (numLAZ != 0):
            error('Folder %s should contain LAS or LAZ but not both!' % inFile, outFolder)
        if numLAS:
            inputFiles = [inFile + '/*.las',]
        elif numLAZ:
            inputFiles = [inFile + '/*.laz',]
        else:
            error('Folder %s does not contain LAS or LAZ files' % inFile, outFolder)
    # A MESH
    elif inType == utils.MESH_FT:
        tmode = '--mode polyMesh --convert --reposition'
        inputFiles = glob.glob(inFile + '/*.obj') + glob.glob(inFile + '/*.OBJ') 
    # A PICTURE
    elif inType == utils.PIC_FT:
        tmode = '--mode picturePlane'
        inputFiles = glob.glob(inFile + '/*.png') + glob.glob(inFile + '/*.jpg') + glob.glob(inFile + '/*.jpeg') + glob.glob(inFile + '/*.PNG') + glob.glob(inFile + '/*.JPG') + glob.glob(inFile + '/*.JPEG')
    
    if len(inputFiles) > 1:
        error('Multiple valid files found in %s' % inFile,outFolder)
    elif len(inputFiles) == 0:
        error('None valid files found in %s' % inFile,outFolder)
    filename = inputFiles[0]
    logFile = os.path.join(outFolder, outputPrefix + '.log')
    
    # Call CONVERTER_COMMAND for the inputFile
    command = CONVERTER_COMMAND + ' ' + tmode + ' --outputPrefix ' + \
        outputPrefix + ' --files ' + os.path.basename(filename)
    if color8Bit:
        command += ' --8bitColor '
    if aligned:
        command += ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + \
            ' ' + str(abOffsetZ)
    command += ' &> ' + logFile
    logging.info(command)
    args = shlex.split(command)
    subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE).communicate()

    # move files to outFolder; drop outputPrefix from filename
    logging.info("Moving files to " + outFolder)
    outputFiles = glob.glob(outputPrefix + '*')
    for filename in outputFiles:
        shutil.move(os.path.abspath(filename), os.path.join(outFolder,filename))

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*' + ofile)))
    if len(ofiles) == 0:
        error('none OSG file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile, outFolder)
    else:
        mainOsgb = ofiles[0]
        if not (inType == utils.PC_FT and inKind == utils.BG_FT):
            # if not a PC BACK
            xmlfiles = glob.glob(os.path.join(outFolder, '*xml'))
            if len(xmlfiles) == 0:
                error('none XML file was generated (found in ' +
                             outFolder + '). Check log: ' + logFile, outFolder)
                xmlPath = None
            else:
                xmlPath = xmlfiles[0]
                if len(xmlfiles) > 1:
                    error('multiple XMLs file were generated (found in '
                                 + outFolder + '). Using ' + xmlPath, outFolder)
            # upate xml file
            updateXMLDescription(xmlPath, cursor, inType, itemId)
        txtfiles = glob.glob(os.path.join(outFolder, '*offset.txt'))
        if len(txtfiles):
            txtFile = txtfiles[0]
            offsets = open(txtFile, 'r').read().split('\n')[0] \
                .split(':')[1].split()
            for i in range(len(offsets)):
                offsets[i] = float(offsets[i])
        elif aligned:
            logging.warn('No offset file was found and it was expected!')
    # We move back to the current working directory
    os.chdir(cwd)
    
def extract_inType(abspath, site_id, osgDir):
    '''
    Checks the type of the input file using the file location
    '''
    if '/MESH/' in abspath:
        inType = utils.MESH_FT
    elif '/PICT/' in abspath:
        inType = utils.PIC_FT
    elif '/PC/' in abspath:
        inType = utils.PC_FT
    else:
        msg = 'could not determine type from abspath'
        logging.error(msg)
        raise Exception(msg)
    if '/SITE/' in abspath:
        inKind = utils.SITE_FT
    elif '/BACK/' in abspath:
        inKind = utils.BG_FT
    else:
        msg  = 'could not determine kind from abspath'
        logging.error(msg)
        raise Exception(msg)
    # Determine period CURR/ARCH_REC/HIST of MESH/PICT
    if any(substring in abspath for substring in ['/MESH/', 'PICT']):
        if '/CURR/' in abspath:
            period = 'CURR'
        elif '/ARCH_REC/' in abspath:
            period = 'ARCH_REC'
        elif '/HIST/' in abspath:
            period = 'HIST'
        else:
            raise Exception('Could not determine period CURR/ARCH_REC/HIST')
    # define outFolder from osgDir and inType
    if (inType == utils.PC_FT and inKind == utils.SITE_FT):
        outFolder = os.path.join(os.path.abspath(osgDir), utils.PC_FT,
                                 inKind, 'S'+str(site_id),
                                 os.path.basename(os.path.normpath(abspath)))
    elif (inType == utils.PC_FT and inKind == utils.BG_FT):
        outFolder = os.path.join(os.path.abspath(osgDir), utils.PC_FT,
                                 inKind,
                                 os.path.basename(os.path.normpath(abspath)))
    elif ((inType == utils.MESH_FT or inType == utils.PIC_FT)
          and (inKind == utils.BG_FT)):
        outFolder = os.path.join(os.path.abspath(osgDir), inType, inKind,
                                 period, os.path.basename
                                 (os.path.normpath(abspath)))
    else:
        outFolder = os.path.join(os.path.abspath(osgDir), inType, inKind,
                                 period, 'S'+str(site_id),
                                 os.path.basename(os.path.normpath(abspath)))
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
    # We move back to the current working directory
    os.chdir(cwd)
    raise Exception(errorMessage)


def run(opts):
    # Start logging
    #logname = os.path.basename(__file__) + '.log'
    logname = os.path.splitext(os.path.basename(__file__))[0] + '.log'
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
SELECT raw_data_item_id, abs_path 
FROM RAW_DATA_ITEM JOIN ITEM USING (item_id) 
WHERE NOT background AND raw_data_item_id NOT IN (
          SELECT raw_data_item_id FROM OSG_DATA_ITEM_PC_SITE 
          UNION 
          SELECT raw_data_item_id FROM OSG_DATA_ITEM_MESH 
          UNION 
          SELECT raw_data_item_id FROM OSG_DATA_ITEM_PICTURE)"""
        # Get the list of items that are not converted yet (we sort by background to have the background converted first)
        raw_data_items, num_raw_data_items = utils.fetchDataFromDB(cursor, query)
        for (rawDataItemId, absPath) in raw_data_items:
            if opts.itemid == '':
                createOSG(cursor, rawDataItemId, opts.osgDir)
            else:
                m = '\t'.join((str(rawDataItemId),absPath))
                print m
                logging.info(m)
    else:
        for rawDataItemId in opts.itemid.split(','):
            createOSG(cursor, int(rawDataItemId), opts.osgDir)    

    # close DB connection
    utils.closeConnectionDB(connection, cursor)
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logging.info(msg)

def argument_parser():
    """ Define the arguments and return the parser object"""
    description = "Generates the OSG data for a raw data item."
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i','--itemid',default='',
                       help='Comma-separated list of Raw Data Item Ids [default is to convert all raw data items related to sites that do not have a related OSG data item] (with ? the available raw data items are listed, with ! the list all the raw data items without any related OSG data item)',
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
    parser.add_argument('-o', '--osgDir', default=utils.DEFAULT_OSG_DATA_DIR,
                        help='OSG data directory [default ' +
                        utils.DEFAULT_OSG_DATA_DIR + ']', action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=utils.LOG_LEVELS_LIST,
                        default=utils.DEFAULT_LOG_LEVEL)
    return parser


if __name__ == "__main__":
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
