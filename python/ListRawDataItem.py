#!/usr/bin/env python
##############################################################################
# Description:      Script to remove a raw data item and the related POTree/OSG
#
# Authors:          Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
#                   Elena Ranguelova, NLeSc
# Created:          16.02.2015
# Last modified:    06.03.2015
#
# Changes:          * Can delete a list of raw data items
#
# Notes:            * User gives an ID from raw_data_item_id
#                   * The absPath of the raw data item is retrieved
#                   * The absPath of related (OSG/POTree) data item are retrieved
#                   * All the previous data is deleted
##############################################################################
import argparse, os, utils, time, shutil

def argument_parser():
    description = "List the Raw data items that are in the DB."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('-l', '--log', help='Log level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=utils.DEFAULT_LOG_LEVEL)

    return parser 

#------------------------------------------------------------------------------        
def run(args): 
    
    logname = os.path.basename(__file__).split('.')[0] + '.log'
    logger = utils.start_logging(filename=logname, level=args.log)
    localtime = utils.getCurrentTimeAsAscii()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logger.info(msg)

     # start timer
    t0 = time.time()
    
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 

    utils.listRawDataItems(cursor)
    
if __name__ == '__main__':
    run( apply_argument_parser() )