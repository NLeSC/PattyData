#!/usr/bin/env python

###############################################################################
# Description: Script to add new data item to RAW data structure
# Author: Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
# Creation date: 21.01.2015
# Modification date:
# Modifications:
# Notes:
#
# DIR structure RAW:
#   RAW
#     |- PC
#         |_ BACK
#         |- SITE
#               |- S1
#               |- ...
#               |- Sn
#     |- MESH
#           |- BACK
#                 |- CURR
#                 |- ARCH_REC
#           |- SITE
#                 |- CURR
#                       |- S1
#                       |- ...
#                       |- Sn
#                 |- ARCH_REC
#                           |- S1
#                           |- ...
#                           |- Sn
#     |- PICT
#           |- BACK
#                 |- CURR
#                 |- HIST
#           |- SITE
#                 |- CURR
#                       |- S1
#                       |- ...
#                       |- Sn
#                 |- HIST
#                       |- S1
#                       |- ...
#                       |- Sn
###############################################################################

import re
import os
import shutil
import argparse
import utils
import json

logger = None


def check_required_options(opts):
    logger.info('Checking if all required arguments are specified.')
    if (opts.type == utils.MESH_FT):  # MESHES should have a period defined
        if not (opts.period == utils.CURR_FT or opts.period ==
                utils.ARCREC_FT):
            logger.error("[ERROR] Period should be '" + utils.CURR_FT +
                         "' or '" + utils.ARCREC_FT + "'")
            parser.error("Period should be '" + utils.CURR_FT + "' or '" +
                         utils.ARCREC_FT + "'")
    elif (opts.type == utils.PIC_FT):  # PICTURES should have a period defined
        if not (opts.period == utils.CURR_FT or
                opts.period == utils.HIST_FT):
            logger.error(
                "[ERROR] Period should be '" + utils.CURR_FT + "' or '" +
                utils.HIST_FT + "' (--period)")
            parser.error("Period should be '" + utils.CURR_FT + "' or '" +
                         utils.HIST_FT + "' (--period)")
    # SITES should have a site number defined
    if (opts.kind == utils.SITE_FT):
        if not (opts.siteno):
            logger.error(
                "[ERROR] Site number should be defined for " + utils.SITE_FT +
                " (--siteno)")
            parser.error("Site number should be defined for " + utils.SITE_FT +
                         " (--siteno)")


def check_directory_structure(RAW_BASEDIR):
    logger.info('Checking if required directory structure exists.')
    # directory structure
    DIRS = [os.path.join(RAW_BASEDIR, utils.PC_FT, utils.BG_FT),
            os.path.join(RAW_BASEDIR, utils.PC_FT, utils.SITE_FT),
            os.path.join(RAW_BASEDIR, utils.MESH_FT, utils.BG_FT),
            os.path.join(RAW_BASEDIR, utils.MESH_FT, utils.SITE_FT),
            os.path.join(RAW_BASEDIR, utils.PIC_FT, utils.BG_FT),
            os.path.join(RAW_BASEDIR, utils.PIC_FT, utils.SITE_FT)]
    # check if the directory structure exist, raise IOError if needed
    for directory in DIRS:
        if not os.path.isdir(directory):
            # os.makedirs(directory) # create directories recursively
            logger.error(
                "[ERROR] Required directory does not exist: " + directory)
            raise IOError("Required directory does not exist: " + directory)


def check_input_data(opts):
    logger.info('Checking input data.')
    # name of Raw Data item may not contain (CURR, BACK, OSG)
    if any(substring in opts.file for substring in ['CURR', 'BACK', 'OSG']):
        logger.error("[ERROR] Input data may not contain (CURR, BACK, OSG)")
        raise IOError("Input data may not contain (CURR, BACK, OSG)")
    # All pictures must have JSON file with same name (.png.json)
    # with at least srid, x, y, z
    if (opts.type == 'PIC_FT'):
        # if input is a directory
        if os.path.isdir(opts.file):
            src_files = os.listdir(opts.file)
            for file_name in src_files:
                # check for figures in directory
                if (os.path.splitext(testname)[1][1:].lower() in ['png',
                                                                  'jpg',
                                                                  'jpeg']):
                    if (os.path.isfile(os.path.join(opts.file,
                                                    file_name) + '.json')):
                        check_json_file(os.path.join(opts.file,
                                                     file_name) + '.json')
                    else:
                        logger.warning("No accompanying JSON file found for " +
                                       "input: " + file_name)
        # if input is a file and is indeed a figure:
        elif (os.path.isfile(opts.file) and os.path.splitext(
              testname)[1][1:].lower() in ['png', 'jpg', 'jpeg']):
            # check for json file ${filename}.json
            if (opts.file + '.json'):
                check_json_file(opts.file + '.json')
            else:
                logger.warning("No accompanying JSON file found for input: " +
                               opts.file)
    # SRID for PCs must not be null
    if (opts.type == 'PC_FT'):
        # lasheader
        srid = utils.readSRID(lasheader)


def check_json_file(jsonfile):
    # check the content of the JSON file
    JSON = json.load(open(jsonfile))
    if all(substring in JSON.keys() for substring in ['x', 'y', 'z', 'srid']):
        pass
    else:
        logger.error("[ERROR] json file should contain at least (x,y,z,srid)")
        raise Exception("json file should contain at least (x,y,z,srid)")


def define_create_target_dir(opts):
    logger.info('Creating target directory.')
    target_basedir = os.path.join(opts.data, opts.type, opts.kind)
    # name of input data, only basename, extensions removed
    inputname = os.path.splitext(os.path.basename(opts.file))[0]
    # 8bit / alignment options
    eightbitinfo, alignmentinfo = "", ""  # default
    if (opts.eight and (opts.type == utils.MESH_FT or
                        (opts.type == utils.PC_FT and opts.kind ==
                         utils.SITE_FT))):
        # check if inputname already contains alignment information
        if any(substring in inputname.lower() for substring in ['8bit',
                                                                '8bc']):
            # 8bitcolor info already in folder name
            pass
        else:
            eightbitinfo = "_8BC"
    if (opts.aligned and opts.kind == utils.SITE_FT and (utils.type == PC_FT
                                                         or utils.type ==
                                                         MESH_FT)):
        # check if inputname already contains alignment information
        if any(substring in inputname.lower() for substring in ['aligned']):
            # check if alignment info in inputname is correct
            if opts.aligned not in inputname:
                logger.error('[ERROR] alignment info in filename does ' +
                             'not match specified alignment argument.')
                raise Exception('[ERROR] alignment info in filename ' +
                                'does not match specified alignment ' +
                                'argument.')
            else:
                pass
        else:
            alignmentinfo = "_ALIGNED_"+opts.aligned
    al8bit = alignmentinfo+eightbitinfo

    # TARGETDIR for PC
    if (opts.type == utils.PC_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(
            target_basedir, inputname)
    if (opts.type == utils.PC_FT and opts.kind == utils.SITE_FT):
        if (opts.aligned):
            # check if background used for the alignment exists
            if (os.path.isdir(os.path.join(
                              opts.data, utils.PC_FT, utils.BG_FT,
                              os.path.splitext(
                                  os.path.basename(opts.aligned))[0]))):
                alignedTo = os.path.splitext(os.path.basename(opts.file))[0]
            else:
                logger.error('Alignment background does not exist: ' +
                             os.path.splitext(os.path.basename(
                                 opts.aligned))[0])
                raise IOError('Alignment background does not exist: ' +
                              os.path.splitext(os.path.basename(
                                  opts.aligned))[0])
        TARGETDIR = os.path.join(target_basedir, 'S'+str(opts.siteno),
                                 inputname+al8bit)
    # TARGETDIR for MESH
    if (opts.type == utils.MESH_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(target_basedir,
                                 opts.period,
                                 inputname+al8bit)
    if (opts.type == utils.MESH_FT and opts.kind == utils.SITE_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period,
                                 'S'+str(opts.siteno),
                                 inputname+al8bit)
    # TARGETDIR for PICT
    if (opts.type == utils.PIC_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period)
    if (opts.type == utils.PIC_FT and opts.kind == utils.SITE_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period,
                                 'S'+str(opts.siteno))
    # check if TARGETDIR exists, create otherwise
    if not os.path.isdir(TARGETDIR):
        os.makedirs(TARGETDIR)  # create directories recursively
    else:
        if not (opts.type == utils.PIC_FT):
            # Raise error if TARGETDIR exists
            # REMOVE/RECREATE to overwrite in future?
            logger.error(TARGETDIR + ' already exists, exiting.')
            raise IOError(TARGETDIR + ' already exists, exiting.')
        pass
    logger.info('Finished creating target directory '+TARGETDIR)
    return TARGETDIR


def copy_data(opts, TARGETDIR):
    logger.info('Copying data.')
    # if input was a directory:
    # copy everything inside the directory to TARGETDIR
    if os.path.isdir(opts.file):
        src_files = os.listdir(opts.file)
        for file_name in src_files:
            if (os.path.isfile(os.path.join(opts.file, file_name))):
                shutil.copy(os.path.join(opts.file, file_name), TARGETDIR)
    # if input was a file:
    # copy the file to TARGETDIR
    elif os.path.isfile(opts.file):
        # create a directory name from the filename
        basedir = os.path.splitext(opts.file)[0]
        os.makedirs(os.path.join(TARGETDIR, basedir))
        # copy the data
        shutil.copyfile(opts.file, os.path.join(TARGETDIR, basedir,
                                                os.path.basename(opts.file)))
        # check if there is an accompanying json file
        if os.path.isfile(opts.file + '.json'):
            shutil.copyfile(opts.file + '.json',
                            os.path.join(TARGETDIR, basedir,
                                         os.path.basename
                                         (opts.file + '.json')))
    else:
        try:
            # remove TARGETDIR if input file does not exist
            # and TARGETDIR is empty
            os.rmdir(TARGETDIR)
        except OSError:
            # TARGETDIR is not empty
            pass
        logger.error(
            "[ERROR] Input file/directory given as argument for " +
            "--file does not exist: " + opts.file)
        raise IOError("Input file/directory given as argument for " +
                      "--file does not exist: " + opts.file)
    logger.info("Finished copying data to " + TARGETDIR)


def main(opts):
    # set logging level
    global logger
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script AddRawDataItem.py')
    logger.info('#######################################')
    # check if all required options are specified
    check_required_options(opts)
    # check if the required directory structure exists
    check_directory_structure(opts.data)
    # check input data
    check_input_data(opts)
    # define target directory
    TARGETDIR = define_create_target_dir(opts)
    # copy the data to the target directory
    copy_data(opts, TARGETDIR)


if __name__ == "__main__":
    # define argument menu
    description = "Add Raw data item to the file structure."
    parser = argparse.ArgumentParser(description=description)
    # create argument groups
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamedPCMESH = parser.add_argument_group(
        'required arguments for ' + utils.PC_FT + ' and ' + utils.MESH_FT)
    requiredNamedMESHPIC = parser.add_argument_group(
        'required arguments for ' + utils.MESH_FT + ' and ' + utils.PIC_FT)
    requiredNamedPC = parser.add_argument_group(
        'required arguments for ' + utils.PC_FT + ' ' + utils.SITE_FT)
    requiredNamedSITE = parser.add_argument_group(
        'required arguments for ' + utils.SITE_FT)
    # fill argument groups
    parser.add_argument('-i', '--data', default=utils.DEFAULT_RAW_DATA_DIR,
                        help='RAW data folder [default ' +
                        utils.DEFAULT_RAW_DATA_DIR + ']')
    requiredNamed.add_argument('-k', '--kind', action='store',
                               help='Type of item',
                               choices=[utils.BG_FT, utils.SITE_FT],
                               required=True)
    requiredNamed.add_argument('-t', '--type', action='store',
                               help='Type of data',
                               choices=[utils.PC_FT, utils.MESH_FT,
                                        utils.PIC_FT], required=True)
    requiredNamed.add_argument('-f', '--file', action='store',
                               help='Input file/directory name to copy',
                               required=True)
    requiredNamedMESHPIC.add_argument('-p', '--period', action='store',
                                      help='Period (choose from ' +
                                      utils.MESH_FT + ':' + utils.CURR_FT +
                                      ',' + utils.ARCREC_FT + '; ' +
                                      utils.PIC_FT + ':' + utils.CURR_FT +
                                      ',' + utils.HIST_FT + ')',
                                      choices=[utils.CURR_FT, utils.HIST_FT,
                                               utils.ARCREC_FT])
    parser.add_argument('-a', '--aligned', action='store',
                        help='Aligned to a specific background [' +
                        'only for PC,MESH SITE]')
    parser.add_argument('--eight', help='8 bit color [only for PC SITE or ' +
                        'MESH]', action="store_true")
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)
    requiredNamedSITE.add_argument('--siteno', action='store',
                                   type=int, help='Site number')
    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
