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

CONVERTER_COMMAND = 'ViaAppia'

# user gives a id from raw data item
# from abspath import from related db entry you get what you deal with
# define out path
# query aligment info and 8bit from db (if necessary)


def getOSGFileFormat(inType):
    return 'osgb'


def updateXMLDescription(xmlPath, siteId, inType, activeObjectId,
                         fileName=None):
    tempFile = xmlPath + '_TEMP'
    ofile = open(tempFile, 'w')
    lines = open(xmlPath, 'r').readlines()
    for line in lines:
        if line.count('<description>'):
            ofile.write('    <description>' +
                        utils.getOSGDescrition
                        (siteId, inType, activeObjectId, os.path.basename
                         (os.path.dirname(fileName))) + '</description>\n')
        else:
            ofile.write(line)
    os.remove(xmlPath)
    shutil.move(tempFile, xmlPath)


def createOSG(inFile, outFolder, inType, opts, logger, abOffsetX=None,
              abOffsetY=None, abOffsetZ=None, color8Bit=False):
    (mainOsgb, xmlPath, offsets) = (None, None, (0, 0, 0))

    if os.path.exists(outFolder):
        shutil.rmtree(outFolder)
    os.makedirs(outFolder)

    # database connection
    connection, cursor = utils.connectToDB(opts.dbname, opts.dbuser,
                                           opts.dbpass, opts.dbhost,
                                           opts.dbport)

    abspath = inFile  # is this correct?
    data_items, num_items = utils.fetchDataFromDB(
        cursor, "SELECT item_id FROM RAW_DATA_ITEM WHERE abs_path = '%s'"
        % (abspath))
    itemID = data_items[0][0]

    # Get 8bitcolor information from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT color_8bit FROM RAW_DATA_ITEM_PC INNER JOIN ' +
        'RAW_DATA_ITEM ON RAW_DATA_ITEM_PC.raw_data_item_id=' +
        'RAW_DATA_ITEM.raw_data_item_id INNER JOIN ITEM ON ' +
        'RAW_DATA_ITEM.item_id = %s' % (itemID))
    color8Bit = data_items[0][0]  # boolean if 8BC

    # Get alignment info from DB
    data_items, num_items = utils.fetchDataFromDB(
        cursor, 'SELECT offset_x, offset_y, offset_z FROM ' +
        'OSG_DATA_ITEM_PC_BACKGROUND INNER JOIN RAW_DATA_ITEM ON ' +
        'OSG_DATA_ITEM_PC_BACKGROUND.raw_data_item_id=' +
        'RAW_DATA_ITEM.raw_data_item_id INNER JOIN ITEM ON ' +
        'RAW_DATA_ITEM.item_id = %s' % (itemID))
    # Set offset if item is aligned
    if len(data_items) > 0:
        (abOffsetX, abOffsetY, abOffsetZ) = data_items[0]

    # close DB connection
    utils.closeConnectionDB(connection, cursor)

    os.chdir(os.path.dirname(inFile))
    outputPrefix = 'data'
    aligned = (abOffsetX is not None)

    ofile = getOSGFileFormat(inType)
    if inType == utils.PC_FT:  # A PC SITE
        tmode = '--mode lodPoints --reposition'
    elif inType == utils.MESH_FT:
        tmode = '--mode polyMesh --convert --reposition'
    elif inType == utils.BG_FT:  # A PC BG
        tmode = '--mode quadtree --reposition'
    elif inType == utils.PIC_FT:
        tmode = '--mode picturePlane'

    command = CONVERTER_COMMAND + ' ' + tmode + ' --outputPrefix ' + \
        outputPrefix + ' --files ' + os.path.basename(inFile)
    if color8Bit:
        command += ' --8bitColor '
    if aligned:
        command += ' --translate ' + str(abOffsetX) + ' ' + str(abOffsetY) + \
            ' ' + str(abOffsetZ)

    logFile = os.path.join(outFolder, outputPrefix + '.log')
    command += ' &> ' + logFile

    logger.info(command)
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     shell=True).communicate()

    # move files to outFolder; drop outputPrefix from filename
    outputFiles = glob.glob(outputPrefix + '*')
    for filename in outputFiles:
        shutil.move(os.path.abspath(filename),
                    os.path.join(outFolder, filename[len(outputPrefix):]))
    logger.info(mvcommand)

    ofiles = sorted(glob.glob(os.path.join(outFolder, '*' + ofile)))
    if len(ofiles) == 0:
        logger.error('none OSG file was generated (found in ' + outFolder +
                     '). Check log: ' + logFile)
        mainOsgb = None
    else:
        mainOsgb = ofiles[0]
        if inType != 'bg':
            xmlfiles = glob.glob(os.path.join(outFolder, '*xml'))
            if len(xmlfiles) == 0:
                logger.error('none XML file was generated (found in ' +
                             outFolder + '). Check log: ' + logFile)
                xmlPath = None
            else:
                xmlPath = xmlfiles[0]
                if len(xmlfiles) > 1:
                    logger.error('multiple XMLs file were generated (found in '
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
    # doesn't work yet, what are the input variables?
    updateXMLDescription(xmlPath, itemID, inType, activeObjectId)


def main(opts):
    # Define logger and start logging
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script GenerateOSG.py')
    logger.info('#######################################')
    createOSG('/home/ronald/pattytest', '/home/ronald/pattytest/outdir', 'PC',
              opts, logger)

if __name__ == "__main__":
    # define argument menu
    description = "Updates DB from the changes in the XML configuration file"
    parser = argparse.ArgumentParser(description=description)

    # fill argument groups
    parser.add_argument('-i', '--config', help='XML configuration file',
                        action='store')  # required? ID?
    parser.add_argument('-d', '--dbname', default=utils.DEFAULT_DB,
                        help='Postgres DB name [default ' + utils.DEFAULT_DB +
                        ']', action='store')
    parser.add_argument('-u', '--dbuser', default=utils.USERNAME,
                        help='DB user [default ' + utils.USERNAME +
                        ']', action='store')
    parser.add_argument('-p', '--dbpass', help='DB pass', action='store')
    parser.add_argument('-t', '--dbhost', help='DB host', action='store')
    parser.add_argument('-r', '--dbport', help='DB port', action='store')
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
