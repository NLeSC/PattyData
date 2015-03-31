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

import time, os, shutil, argparse, utils, json, liblas, glob

logger = None


def check_required_options(opts):
    """
    Check if all required arguments are specified
    """
    logger.info('Checking if all required arguments are specified.')
    if (opts.type == utils.MESH_FT):  # MESHES should have a period defined
        if not (opts.period == utils.CURR_FT or opts.period ==
                utils.ARCREC_FT):
            logger.error("Period should be '" + utils.CURR_FT +
                         "' or '" + utils.ARCREC_FT + "'")
            parser.error("Period should be '" + utils.CURR_FT + "' or '" +
                         utils.ARCREC_FT + "'")
    elif (opts.type == utils.PIC_FT):  # PICTURES should have a period defined
        if not (opts.period == utils.CURR_FT or
                opts.period == utils.HIST_FT):
            logger.error(
                "Period should be '" + utils.CURR_FT + "' or '" +
                utils.HIST_FT + "' (--period)")
            parser.error("Period should be '" + utils.CURR_FT + "' or '" +
                         utils.HIST_FT + "' (--period)")
    # SITES should have a site number defined
    if (opts.kind == utils.SITE_FT):
        if not (opts.site):
            logger.error(
                "Site number should be defined for " + utils.SITE_FT +
                " (--site)")
            parser.error("Site number should be defined for " + utils.SITE_FT +
                         " (--site)")


def check_directory_structure(RAW_BASEDIR):
    """
    Checks if the required directory structure exists
    """
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
            os.makedirs(directory) # create directories recursively
            logger.info(
                "Required directory created: " + directory)            
#            logger.error(
#                "Required directory does not exist: " + directory)
#            raise IOError("Required directory does not exist: " + directory)


def check_input_data(opts):
    """
    Checks if the input data has the required format
    """
    logger.info('Checking input data.')
    # name of Raw Data item may not contain (CURR, BACK, OSG)
    if any(substring in os.path.basename(opts.file) for substring
           in ['CURR', 'BACK', 'OSG']):
        logger.error("Input data may not contain (CURR, BACK, OSG)")
        raise IOError("Input data may not contain (CURR, BACK, OSG)")
    # All pictures must have JSON file with same name (.png.json)
    # with at least srid, x, y, z
    if (opts.type == utils.PIC_FT):
        # if input is a directory
        if os.path.isdir(opts.file):
            src_files = os.listdir(opts.file)
            for file_name in src_files:
                # check for figures in directory
                if (os.path.splitext(file_name)[1][1:].lower() in ['png',
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
              opts.file)[1][1:].lower() in ['png', 'jpg', 'jpeg']):
            # check for json file ${filename}.json
            if os.path.isfile(opts.file + '.json'):
                check_json_file(opts.file + '.json')
            else:
                logger.warning("No accompanying JSON file found for input: " +
                               opts.file)
    # SRID for PCs must not be null
    if (opts.type == utils.PC_FT):
        if os.path.isfile(opts.file):  # input is file
            lasHeader = liblas.file.File(opts.file, mode='r').header
            srid = utils.readSRID(lasHeader)
            if srid is None:
                logger.warning("srid is not defined in lasheader " + opts.file)
        else:  # input is directory
            files = glob.glob(opts.file + '/*.las') + glob.glob(
                opts.file + '/*.laz')
            for filename in files:
                # check all *.las en *.laz files in directory
                lasHeader = liblas.file.File(filename, mode='r').header
                srid = utils.readSRID(lasHeader)
                if srid is None:
                    logger.warning("srid is not defined in lasheader " +
                                   filename)
    # MESH should have an obj extension
    if (opts.type == utils.MESH_FT):
        # if input is a file it should have obj extension:
        if (os.path.isfile(opts.file) and not os.path.splitext(
              opts.file)[1][1:].lower() in ['obj']):
            logger.error('File ' + opts.file +
                         '  has no required obj extension')
            raise IOError('File ' + opts.file
                          + ' has no required obj extension')
        # if input is a directory, then
        # check if there is an obj file in the directory
        elif os.path.isdir(opts.file):
            files = glob.glob(opts.file + '/*.obj')
            if ('.obj' not in [os.path.splitext(x)[1][:] for x in files]):
                logger.error('No file with required obj extension found in ' +
                             'directory ' + opts.file)
                raise IOError('No file with required obj extension found in ' +
                              'directory ' + opts.file)

def check_json_file(jsonfile):
    """
    Checks the content of a JSON file
    """
    JSON = json.load(open(jsonfile))
    if all(substring in JSON.keys() for substring in ['x', 'y', 'z', 'srid']):
        pass
    else:
        logger.error("json file should contain at least (x,y,z,srid)")
        raise Exception("json file should contain at least (x,y,z,srid)")


def srid_8bitcolor_info(inputname, opts):
    """
    Defines 8bit / srid options
    """
    eightbitinfo, sridinfo = "", ""  # default
    if (opts.eight and (opts.type == utils.MESH_FT or
                        (opts.type == utils.PC_FT and opts.kind ==
                         utils.SITE_FT))):
        # check if inputname already contains 8bc information
        if any(substring in inputname.lower() for substring in ['8bit',
                                                                '8bc']):
            # 8bitcolor info already in folder name
            pass
        else:
            eightbitinfo = "_8BC"
    if (opts.srid and opts.kind == utils.SITE_FT and (opts.type ==
                                                      utils.MESH_FT)):
        # check if inputname already contains srid information
        if any(substring in inputname.lower() for substring in ['srid']):
            # check if srid info in inputname is correct
            if opts.srid not in inputname:
                logger.error('SRID info in filename does ' +
                             'not match specified srid argument.')
                raise Exception('SRID info in filename ' +
                                'does not match specified srid ' +
                                'argument.')
            else:
                pass
        else:
            sridinfo = "_SRID_" + opts.srid
    srid8bit = sridinfo + eightbitinfo
    return srid8bit


def define_create_target_dir(opts):
    """
    Defines and creates the target base directory TARGETDIR
    """
    logger.info('Creating target directory.')
    target_basedir = os.path.join(opts.data, opts.type, opts.kind)
    # name of input data, only basename, extensions removed
    inputname = os.path.splitext(os.path.basename(opts.file))[0]
    srid8bit = srid_8bitcolor_info(inputname, opts)

    # TARGETDIR for PC
    if (opts.type == utils.PC_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(
            target_basedir, inputname)
    if (opts.type == utils.PC_FT and opts.kind == utils.SITE_FT):
#        if (opts.aligned):
#            # check if background used for the alignment exists
#            if (os.path.isdir(os.path.join(
#                              opts.data, utils.PC_FT, utils.BG_FT,
#                              os.path.splitext(
#                                  os.path.basename(opts.aligned))[0]))):
#                alignedTo = os.path.splitext(os.path.basename(opts.file))[0]
#            else:
#                logger.error('Alignment background does not exist: ' +
#                             os.path.splitext(os.path.basename(
#                                 opts.aligned))[0])
#                raise IOError('Alignment background does not exist: ' +
#                              os.path.splitext(os.path.basename(
#                                  opts.aligned))[0])
        TARGETDIR = os.path.join(target_basedir, 'S'+str(opts.site))

    # TARGETDIR for MESH
    if (opts.type == utils.MESH_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(target_basedir,
                                 opts.period,
                                 inputname+srid8bit)
    if (opts.type == utils.MESH_FT and opts.kind == utils.SITE_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period,
                                 'S'+str(opts.site),
                                 inputname+srid8bit)
    # TARGETDIR for PICT
    if (opts.type == utils.PIC_FT and opts.kind == utils.BG_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period)
    if (opts.type == utils.PIC_FT and opts.kind == utils.SITE_FT):
        TARGETDIR = os.path.join(target_basedir, opts.period,
                                 'S'+str(opts.site))
    # check if TARGETDIR exists, create otherwise
    if not os.path.isdir(TARGETDIR):
        os.makedirs(TARGETDIR)  # create directories recursively
    else:
        if not (opts.type == utils.PIC_FT or
                (opts.type == utils.PC_FT and opts.kind == utils.SITE_FT)):
            # Raise error if TARGETDIR exists
            # REMOVE/RECREATE to overwrite in future?
            logger.error(TARGETDIR + ' already exists, exiting.')
            raise IOError(TARGETDIR + ' already exists, exiting.')
        pass
    logger.info('Finished creating target directory '+TARGETDIR)
    return TARGETDIR


def copy_data(opts, TARGETDIR):
    """
    Copies the data into the file structure.
    """
    logger.info('Copying data.')
    # if input was a directory:
    # copy everything inside the directory to TARGETDIR
    if os.path.isdir(opts.file):
        src_files = os.listdir(opts.file)
        # for PC SITE and PICT put all files in their own subdirectory
        if ((opts.type == utils.PC_FT and opts.kind == utils.SITE_FT
             ) or (opts.type == utils.PIC_FT)):
            for file_name in src_files:
                basedir = os.path.splitext(file_name)[0]
                if (os.path.isfile(os.path.join(opts.file, file_name))):
                    # check 8bit/srid info already in filename
                    # so we don't duplicate it in the folder name
                    srid8bit = srid_8bitcolor_info(file_name, opts)
                    if not os.path.isdir(os.path.join
                                         (TARGETDIR, basedir + srid8bit)):
                        os.mkdir(os.path.join(TARGETDIR, basedir + srid8bit))
                        #print file_name
                        shutil.copyfile(os.path.join(opts.file, file_name),
                                        os.path.join(TARGETDIR, basedir +
                                                     srid8bit, file_name))
                    else:
                        logger.error(os.path.join
                                     (TARGETDIR, basedir + srid8bit) +
                                     ' already exists, exiting.')
                        raise IOError(os.path.join
                                      (TARGETDIR, basedir + srid8bit) +
                                      ' already exists, exiting.')
        else:
            for file_name in src_files:
                if (os.path.isfile(os.path.join(opts.file, file_name))):
                    #print file_name
                    shutil.copy(os.path.join(opts.file, file_name), TARGETDIR)
    elif (os.path.isfile(opts.file) and opts.type != utils.MESH_FT):
        # if input was a file:
        # copy the file to TARGETDIR
        # create a directory name from the filename
        basedir = os.path.basename(os.path.splitext(opts.file)[0])
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
    elif (os.path.isfile(opts.file) and opts.type == utils.MESH_FT):
        # if input is a filename and is a MESH
        # copy all data in the underlying directory
        for filename in glob.glob(os.path.dirname(opts.file)+'/*'):
            shutil.copyfile(filename, os.path.join(TARGETDIR,
                                                   os.path.basename(filename)))
    else:
        try:
            # remove TARGETDIR if input file does not exist
            # and TARGETDIR is empty
            os.rmdir(TARGETDIR)
        except OSError:
            # TARGETDIR is not empty
            pass
        logger.error(
            "Input file/directory given as argument for " +
            "--file does not exist: " + opts.file)
        raise IOError("Input file/directory given as argument for " +
                      "--file does not exist: " + opts.file)
    logger.info("Finished copying data to " + TARGETDIR)


def run(opts):
    # set logging level
    global logger
    #logname = os.path.basename(__file__) + '.log'
    logname = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logger = utils.start_logging(filename=logname, level=opts.log)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logger.info(msg)
    
    opts.file = opts.file.rstrip('/')
    
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
    
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logger.info(msg)

def argument_parser():
    """ Define the arguments and return the parser object"""
    description = "Add Raw data item to the file structure."
    parser = argparse.ArgumentParser(description=description)
    # create argument groups
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamedPCMESH = parser.add_argument_group('required arguments for ' + utils.PC_FT + ' and ' + utils.MESH_FT)
    requiredNamedMESHPIC = parser.add_argument_group('required arguments for ' + utils.MESH_FT + ' and ' + utils.PIC_FT)
    requiredNamedPC = parser.add_argument_group('required arguments for ' + utils.PC_FT + ' ' + utils.SITE_FT)
    requiredNamedSITE = parser.add_argument_group('required arguments for ' + utils.SITE_FT)
    
    # fill argument groups
    parser.add_argument('-i', '--data', default=utils.DEFAULT_RAW_DATA_DIR,help='RAW data folder [default ' + utils.DEFAULT_RAW_DATA_DIR + ']')
    requiredNamed.add_argument('-k', '--kind', action='store', help='Type of item', choices=[utils.BG_FT, utils.SITE_FT], required=True)
    requiredNamed.add_argument('-t', '--type', action='store', help='Type of data', choices=[utils.PC_FT, utils.MESH_FT, utils.PIC_FT], required=True)
    requiredNamed.add_argument('-f', '--file', action='store', help='Input file/directory name to copy', required=True)
    requiredNamedMESHPIC.add_argument('-p', '--period', action='store', help='Period (choose from ' + utils.MESH_FT + ':' + utils.CURR_FT + ',' + utils.ARCREC_FT + '; ' +  utils.PIC_FT + ':' + utils.CURR_FT + ',' + utils.HIST_FT + ')', choices=[utils.CURR_FT, utils.HIST_FT, utils.ARCREC_FT])
    parser.add_argument('-s', '--srid', action='store', help='spatial reference system SRID [only for MESH SITE]')
    parser.add_argument('--eight', help='8 bit color [only for PC SITE or MESH]', action="store_true")
    parser.add_argument('-l', '--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    requiredNamedSITE.add_argument('--site', action='store', type=int, help='Site number')
    return parser

if __name__ == "__main__":
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
