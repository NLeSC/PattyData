#!/usr/bin/env python

###############################################################################
# Description: Script to add new data item to RAW data structure
# Author: Ronald van Haren, NLeSC, r.vanharen@esciencecenter.nl
# Creation date: 21.01.2015
# Modification date:
# Modifications:
# Notes:
###############################################################################

import optparse
import re
import os
import shutil
import logging
import argparse
import utils

# global variables
PC_DIR = "PC"
MESHES_DIR = "MESH"
PICTURES_DIR = "PICT"
BACKGROUND_DIR = "BACK"
SITES_DIR = "SITE"


def check_required_options(opts, logger):
    logger.info('Checking if all required arguments are specified.')
    if (opts.type == "MESH"):  # MESHES should have a period defined
        if not (opts.period == "CURR" or opts.period == "HIST"):
            logger.error("[ERROR] Period should be 'CURR' or 'HIST'")
            parser.error("Period should be 'CURR' or 'HIST'")
    elif (opts.type == "PICT"):  # PICTURES should have a period defined
        if not (opts.period == "CURR" or opts.period == "ARCH_REC"):
            logger.error(
                "[ERROR] Period should be 'CURR' or 'ARCH_REC' (--period)")
            parser.error("Period should be 'CURR' or 'ARCH_REC' (--period)")
    # SITES should have a site number defined
    if (opts.kind == "SITE"):
        if not (opts.siteno):
            logger.error(
                "[ERROR] site number should be defined for SITE (--siteno)")
            parser.error("site number should be defined for SITE (--siteno)")
    # PC/MESHES should have a version/reconstruction number defined
    if (opts.type == "PC" or opts.type == "MESH"):
        if not (opts.verrecno):
            logger.error("[ERROR] Version/reconstruction " +
                         "number should be defined (--verrecno)")
            parser.error(
                "Version/reconstruction number should be defined (--verrecno)")


def check_directory_structure(RAW_BASEDIR, logger):
    logger.info('Checking if required directory structure exists.')
    # directory structure
    DIRS = [os.path.join(RAW_BASEDIR, PC_DIR, BACKGROUND_DIR),
            os.path.join(RAW_BASEDIR, PC_DIR, SITES_DIR),
            os.path.join(RAW_BASEDIR, MESHES_DIR, BACKGROUND_DIR),
            os.path.join(RAW_BASEDIR, MESHES_DIR, SITES_DIR),
            os.path.join(RAW_BASEDIR, PICTURES_DIR, BACKGROUND_DIR),
            os.path.join(RAW_BASEDIR, PICTURES_DIR, SITES_DIR)]
    # check if the directory structure exist, raise IOError if needed
    for directory in DIRS:
        if not os.path.isdir(directory):
            # os.makedirs(directory) # create directories recursively
            logger.error(
                "[ERROR] Required directory does not exist: " + directory)
            raise IOError("Required directory does not exist: " + directory)


def define_create_target_dir(opts, logger):
    logger.info('Creating target directory.')
    target_basedir = os.path.join(opts.data, opts.type, opts.kind)
    # name of input data, only basename, extensions removed
    inputname = os.path.splitext(os.path.basename(opts.file))[0]
    # TARGETDIR for PC
    if (opts.type == "PC" and opts.kind == "BACK"):
        TARGETDIR = os.path.join(
            target_basedir, inputname+'V'+str(opts.verrecno))
    if (opts.type == "PC" and opts.kind == "SITE"):
        if (opts.aligned):
            # check if background used for the alignment exists
            if (os.path.isdir(os.path.join(
                              opts.data, PC_DIR, BACKGROUND_DIR,
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
        if (opts.eight and opts.aligned):
            al8bit = "_ALIGNED_"+opts.aligned+"_8BC"
        elif (opts.eight and not opts.aligned):
            al8bit = "_8BC"
        elif (opts.aligned and not opts.eight):
            al8bit = "_ALIGNED_"+opts.aligned
        else:
            al8bit = ""
        TARGETDIR = os.path.join(target_basedir, 'S'+str(opts.siteno),
                             inputname+'V'+str(opts.verrecno)+al8bit)
    # TARGETDIR for MESH
    if (opts.type == "MESH" and opts.kind == "BACK"):
        TARGETDIR = os.path.join(target_basedir,
                                 opts.period, inputname+'V'+str(opts.verrecno))
    if (opts.type == "MESH" and opts.kind == "SITE"):
        TARGETDIR = os.path.join(target_basedir, 'S'+str(opts.siteno),
                                 opts.period, inputname+'V'+str(opts.verrecno))
    # TARGETDIR for PICT
    if (opts.type == "PICT" and opts.kind == "BACK"):
        TARGETDIR = os.path.join(target_basedir, opts.period)
    if (opts.type == "PICT" and opts.kind == "SITE"):
        TARGETDIR = os.path.join(target_basedir,
                                 'S'+str(opts.siteno), opts.period)
    # check if TARGETDIR exists, create otherwise
    if not os.path.isdir(TARGETDIR):
        os.makedirs(TARGETDIR)  # create directories recursively
    else:
        # Raise error if TARGETDIR exists
        # REMOVE/RECREATE to overwrite in future?
        logger.error(TARGETDIR + ' already exists, exiting.')
        raise IOError(TARGETDIR + ' already exists, exiting.')
    logger.info('Finished creating target directory '+TARGETDIR)
    return TARGETDIR


def copy_data(opts, TARGETDIR, logger):
    logger.info('Copying data.')
    # if input was a directory:
    # copy everything inside the directory to TARGETDIR
    if os.path.isdir(opts.file):
        src_files = os.listdir(opts.file)
        for file_name in src_files:
            if (os.path.isfile(os.path.join(opts.file, file_name))):
                shutil.copy(os.path.join(opts.file, file_name), TARGETDIR)
    elif os.path.isfile(opts.file):
        shutil.copyfile(opts.file, TARGETDIR)
    # if input was a file:
    # copy the file to TARGETDIR
    elif os.path.isfile(opts.file):
        src_files = os.listdir(opts.file)
        for file_name in src_files:
            if (os.path.isfile(os.path.join(opts.file, file_name))):
                shutil.copy(os.path.join(opts.file, file_name), TARGETDIR)
    else:
        logger.error(
            "[ERROR] Input file/directory given as argument for " +
            "--file does not exist: " + opts.file)
        raise IOError("Input file/directory given as argument for " +
                      "--file does not exist: " + opts.file)
    logger.info("Finished copying data to " + TARGETDIR)



def main(opts):
    # set logging level
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script AddRawDataItem.py')
    logger.info('#######################################')
    # check if all required options are specified
    check_required_options(opts, logger)
    # check if the required directory structure exists
    check_directory_structure(opts.data, logger)
    # define target directory
    TARGETDIR = define_create_target_dir(opts, logger)
    # copy the data to the target directory
    copy_data(opts, TARGETDIR, logger)


if __name__ == "__main__":
    # define argument menu
    description = "Add Raw data item to the file structure."
    parser = argparse.ArgumentParser(description=description)
    # create argument groups
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamedPCMESH = parser.add_argument_group(
        'required arguments for PC and MESH')
    requiredNamedMESHPIC = parser.add_argument_group(
        'required arguments for MESH and PICT')
    requiredNamedPC = parser.add_argument_group(
        'required arguments for PC SITE')
    requiredNamedSITE = parser.add_argument_group(
        'required arguments for SITE')
    # fill argument groups
    parser.add_argument('-i', '--data', default=utils.DEFAULT_RAW_DATA_FOLDER,
                        help='RAW data folder [default ' +
                        utils.DEFAULT_RAW_DATA_FOLDER + ']')
    requiredNamed.add_argument('-k', '--kind', action='store',
                               help='Type of item',
                               choices=['BACK', 'SITE'], required=True)
    requiredNamed.add_argument('-t', '--type', action='store',
                               help='Type of data',
                               choices=['PC', 'MESH', 'PICT'], required=True)
    requiredNamed.add_argument('-f', '--file', action='store',
                               help='Input file/directory name to copy',
                               required=True)
    requiredNamedPCMESH.add_argument('--verrecno', action='store', type=int,
                                     help='Version or reconstruction number')
    requiredNamedMESHPIC.add_argument('-p', '--period', action='store',
                                      help='Period (choose from ' +
                                      'MESH:CURR,ARCH_REC; PICT:CURR,HIST)',
                                      choices=['CURR', 'HIST', 'ARCH_REC'])
    requiredNamedPC.add_argument('-a', '--aligned', action='store',
                                 help='Aligned to a specific background')
    parser.add_argument('--eight', help='8 bit color [only for PC SITE]',
                        action="store_true")
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'error'],
                        default=utils.DEFAULT_LOG_LEVEL)
    requiredNamedSITE.add_argument('--siteno', action='store',
                                   type=int, help='Site number')
    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
