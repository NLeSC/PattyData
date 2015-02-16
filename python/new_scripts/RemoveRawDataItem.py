#!/usr/bin/env python
##############################################################################
# Description:      Script to remove a raw data item and the related POTree/OSG
#
# Authors:          Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
#
# Created:          16.02.2015
# Last modified:    16.02.2015
#
# Changes:
#
# Notes:            * User gives an ID from raw_data_item_id
#                   * The absPath of the raw data item is retrieved
#                   * The absPath of related (OSG/POTree) data item are retrieved
#                   * All the previous data is deleted
##############################################################################
import re
import os
import shutil
import argparse
import utils
import json
import liblas
import glob

logger = None

def remove_data(opts):
    """
    Removes the data from the file structure.
    """
    logger.info('Removing data.')
    logger.info("Finished copying data to " + TARGETDIR)

def main(opts):
    # set logging level
    global logger
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=opts.log)
    logger.info('#######################################')
    logger.info('Starting script RemoveRawDataItem.py')
    logger.info('#######################################')

    # copy the data to the target directory
    remove_data(opts)


if __name__ == "__main__":
    # define argument menu
    description = "Removes a Raw data item and the related converted data from the file structure."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-i', '--itemid', help='Raw data item id (with ? the available raw data items are listed)',
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
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)
    # extract user entered arguments
    opts = parser.parse_args()

    # run main
    main(opts)
