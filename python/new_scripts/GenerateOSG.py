#!/usr/bin/env python
##############################################################################
# Description:
# Authors:          Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
#                   Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
# Created:          26.01.2015
# Last modified:    28.01.2015
# Changes:
# Notes:
##############################################################################

import shutil
import os
import utils
import glob
import subprocess
import argparse

logger = None

CONVERTER_COMMAND = 'ViaAppia'

# user gives a id from raw data item
# from abspath import from related db entry you get what you deal with
# define out path
# query aligment info and 8bit from db (if necessary)


def getOSGFileFormat(inType):
    return 'osgb'


def updateXMLDescription(xmlPath, relPath):
    # update description in xml file using unique identifier -> relative path
    tempFile = xmlPath + '_TEMP'
    ofile = open(tempFile, 'w')
    lines = open(xmlPath, 'r').readlines()
    for line in lines:
        if line.count('<description>'):
            ofile.write('    <description>' +
                        relPath + '</description>\n')
        else:
            ofile.write(line)
    os.remove(xmlPath)
    shutil.move(tempFile, xmlPath)


def createOSG(opts, abOffsetX=None,
              abOffsetY=None, abOffsetZ=None, color8Bit=False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))

    # database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)
    # extract abspath using raw_data_item_id
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT abs_path FROM RAW_DATA_ITEM WHERE " +
        "raw_data_item_id = '%s'" % (opts.itemid))
    abspath = data_items[0][0]

    # extract inType & outFolder, create outFolder in non-existent
    inType, outFolder = extract_inType(abspath, opts.osgDir)
    inFile = abspath  # CORRECT ?

    # Get 8bitcolor information from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT color_8bit FROM RAW_DATA_ITEM_PC INNER JOIN ' +
        'RAW_DATA_ITEM ON RAW_DATA_ITEM_PC.raw_data_item_id=' +
        'RAW_DATA_ITEM.raw_data_item_id WHERE ' +
        'RAW_DATA_ITEM.raw_data_item_id = %s' % (opts.itemid))
    color8Bit = data_items[0][0]  # boolean if 8BC

    # Get alignment info from DB
    # TODO: TEST, no values in DB yet
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT offset_x, offset_y, offset_z FROM ' +
        'OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM ON ' +
        'OSG_DATA_ITEM_PC_BACKGROUND.raw_data_item_id=' +
        'RAW_DATA_ITEM.raw_data_item_id WHERE ' +
        'RAW_DATA_ITEM.raw_data_item_id = %s' % (opts.itemid))

    # Set offset if item is aligned
    if len(data_items) > 0:
        (abOffsetX, abOffsetY, abOffsetZ) = data_items[0]

    # close DB connection
    utils.closeConnectionDB(connection, cursor)

    if os.path.isfile(inFile):
        # input was a file -> change to directory
        os.chdir(os.path.dirname(inFile))
    else:
        # input is already a directory
        os.chdir(inFile)
        #  os.chdir('/home/ronaldvh/test')  # REMOVE, FOR TESTING ONLY

    outputPrefix = 'data'
    aligned = (abOffsetX is not None)
    ofile = getOSGFileFormat(inType)
    if inType == utils.SITE_FT:  # A PC SITE
        tmode = '--mode lodPoints --reposition'
    elif inType == utils.MESH_FT:
        tmode = '--mode polyMesh --convert --reposition'
    elif inType == utils.BG_FT:  # A PC BG
        tmode = '--mode quadtree --reposition'
    elif inType == utils.PIC_FT:
        tmode = '--mode picturePlane'

    if color8Bit:
        command += ' --8bitColor '
    if aligned:
        command += ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + \
            ' ' + str(abOffsetZ)

    logFile = os.path.join(outFolder, outputPrefix + '.log')
    inputFiles = glob.glob(inFile + '/*.las') + glob.glob(
                      inFile + '/*.laz')
    for filename in inputFiles:
        command = CONVERTER_COMMAND + ' ' + tmode + ' --outputPrefix ' + \
            outputPrefix + ' --files ' + os.path.join(os.path.basename(inFile),
                                                      filename)
        command += ' &> ' + logFile

        logger.info(command)
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        shell=True).communicate()

    # move files to outFolder; drop outputPrefix from filename
    outputFiles = glob.glob(outputPrefix + '*')
    for filename in outputFiles:
        shutil.move(os.path.abspath(filename),
                    os.path.join(outFolder, filename[len(outputPrefix)+1:]))
    logger.info("Moving files to " + outFolder)

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*' + ofile)))
    if len(ofiles) == 0:
        logger.error('none OSG file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile)
        raise Exception('none OSG file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile)
    else:
        mainOsgb = ofiles[0]
        if inType != utils.BG_FT:
            xmlfiles = glob.glob(os.path.join(outFolder, '*xml'))
            if len(xmlfiles) == 0:
                logger.error('none XML file was generated (found in ' +
                             outFolder + '). Check log: ' + logFile)
                raise Exception('none XML file was generated (found in ' +
                             outFolder + '). Check log: ' + logFile)
                xmlPath = None
            else:
                xmlPath = xmlfiles[0]
                if len(xmlfiles) > 1:
                    logger.error('multiple XMLs file were generated (found in '
                                 + outFolder + '). Using ' + xmlPath)
                    raise Exception('multiple XMLs file were generated (found in '
                                 + outFolder + '). Using ' + xmlPath)
        txtfiles = glob.glob(os.path.join(outFolder, '*offset.txt'))
        if len(txtfiles):
            txtFile = txtfiles[0]
            offsets = open(txtFile, 'r').read().split('\n')[0] \
                .split(':')[1].split()
            for i in range(len(offsets)):
                offsets[i] = float(offsets[i])
        elif aligned:
            logger.warn('No offset file was found and it was expected!')
    # upate xml file
    updateXMLDescription(xmlPath,
                         os.path.relpath(outFolder,
                                         utils.DEFAULT_RAW_DATA_DIR))

def extract_inType(abspath,osgDir):
    '''
    Checks the type of the input file using the file location
    '''
    if '/MESH/' in abspath:
        inType = utils.MESH_FT
    elif '/PICT/' in abspath:
        inType = utils.PIC_FT
    elif '/PC/SITE/' in abspath:
        inType = utils.SITE_FT
    elif '/PC/BACK/' in abspath:
        inType = utils.BG_FT
    else:
        logger.error('could not determine type from abspath')
        raise Exception('Could not determine type from abspath')
    # define outFolder from osgDir and inType
    if inType in [utils.SITE_FT, utils.BG_FT]:
        outFolder = os.path.join(os.path.abspath(osgDir), utils.PC_FT,
                                 inType, 
                                 os.path.basename(os.path.normpath(abspath)))
    else:
        outFolder = os.path.join(os.path.abspath(osgDir), inType,
                                 os.path.basename(os.path.normpath(abspath)))

    # create outFolder if it does not exist yet
    if not os.path.isdir(outFolder):
        os.makedirs(outFolder)
    else:
        raise IOError('Output folder ' + outFolder + ' already exists, ' +
                      'please remove manually')
        # shutil.rmtree(outFolder)  # if we won't to force remove it
    return inType, outFolder


def main(opts):
    # Define logger and start logging
    global logger
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script GenerateOSG.py')
    logger.info('#######################################')
    createOSG(opts)

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
    parser.add_argument('-o', '--osgDir', default=utils.DEFAULT_OSG_DATA_DIR,
                        help='OSG data directory [default ' +
                        utils.DEFAULT_POTREE_DATA_DIR + ']',action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
