#!/usr/bin/env python
################################################################################
# Description:      Script to update the avg z of items based on the  
#                   cutouts of the footprints
# Author:           Oscar Martintez Rubi, NLeSc, O.Rubi@nlesc.nl                                       
# Creation date:    02.03.2015      
# Modification date: 02.03.2015
# Modifications:   
# Notes:            
################################################################################
import os, argparse, utils, psycopg2, time, logging
import GetItemLAS

BUFFER = 2
CONCAVE = 0.9

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Script to minimum and maximum Z of the items")
    parser.add_argument('-i','--itemid',default='',help='Comma-separated list of item ids to update their avg. Z from cutouts [default all]',type=str, required=False)
    parser.add_argument('-l','--las',default=utils.DEFAULT_BACKGROUND_FOLDER,help='Folder that contains the LAS/LAZ files [default ' + utils.DEFAULT_BACKGROUND_FOLDER + ']',type=str, required=False)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name [default ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
        
    return parser


#------------------------------------------------------------------------------        
def run(args): 
    # start logging
    logname = os.path.basename(__file__) + '.log'
    utils.start_logging(filename=logname, level=utils.DEFAULT_LOG_LEVEL)
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' %localtime
    print msg
    logging.info(msg)
    
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 
    
    itemIds = []
    
    if args.itemid == '':
        data,num = utils.fetchDataFromDB(cursor, 'SELECT item_id FROM ITEM WHERE NOT background')
        for (itemId,) in data:
            itemIds.append(itemId)
    else:
        itemIds = args.itemid.split(',')
    
    for itemId in itemIds:
        logging.info('Getting average Z for item %d' % itemId)
        outputFile = 'temp_%03d.las' % itemId 
        (returnOk, vertices, minZ, maxZ, avgZ, numpoints) = GetItemLAS.create_cut_out(cursor, args.las, outputFile, itemId, BUFFER, CONCAVE)
        
        # We do not need the cutout
        if os.path.isfile(outputFile):
            os.remove(outputFile)
        
        if returnOk:
            utils.dbExecute(cursor, "UPDATE ITEM SET (min_z,max_z) = (%s,%s) WHERE item_id = %s", 
                                [minZ, maxZ, itemId])
    
            
    # close the conection to the DB
    utils.closeConnectionDB(connection, cursor)
    
    # measure elapsed time
    elapsed_time = time.time() - t0    
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logging.info(msg)

if __name__ == '__main__':
    run(utils.apply_argument_parser(argument_parser()))
