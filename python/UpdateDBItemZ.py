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
import os, argparse, utils, time, logging, multiprocessing
import GetItemLAS

BUFFER = 2
CONCAVE = 0.9

def runChild(procIndex, itemsQueue, resultsQueue, lasFolder, dbname, dbuser, dbpass, dbhost, dbport):
    connection, cursor = utils.connectToDB(dbname, dbuser, dbpass, dbhost, dbport) 
    kill_received = False
    while not kill_received:
        itemId = None
        try:
            # This call will patiently wait until new job is available
            itemId = itemsQueue.get()
        except:
            # if there is an error we will quit the generation
            kill_received = True
        if itemId == None:
            # If we receive a None job, it means we can stop this workers 
            # (all the create-image jobs are done)
            kill_received = True
        else:            
            logging.info('PROC%d: Getting minimum and maximum Z for item %d' % (procIndex,itemId))
            outputFile = 'temp_%03d.las' % itemId 
            try:
                (returnOk, vertices, minZ, maxZ, avgZ, numpoints) = GetItemLAS.create_cut_out(cursor, lasFolder, outputFile, itemId, BUFFER, CONCAVE)
            
                # We do not need the cutout
                if os.path.isfile(outputFile):
                    os.remove(outputFile)
            
                if returnOk:
                    logging.info('PROC%d: Updating DB minimum and maximum Z for item %d' % (procIndex,itemId))
                    utils.dbExecute(cursor, "UPDATE ITEM SET (min_z,max_z) = (%s,%s) WHERE item_id = %s", 
                                    [minZ, maxZ, itemId])
            except Exception, e:
                connection.rollback()
                logging.error('PROC%d: Can not update minimum and maximum Z for item %d' % (procIndex,itemId))
                logging.error(e)
            resultsQueue.put((procIndex, itemId))   
    utils.closeConnectionDB(connection, cursor)

def run(args): 
    # start logging
    logname = os.path.splitext(os.path.basename(__file__))[0] + '.log'
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
        
    # close the conection to the DB
    utils.closeConnectionDB(connection, cursor)
    
    # Create queues
    itemsQueue = multiprocessing.Queue() # The queue of tasks (queries)
    resultsQueue = multiprocessing.Queue() # The queue of results
    
    for itemId in itemIds:
        itemsQueue.put(int(itemId))
    for i in range(args.cores): #we add as many None jobs as numUsers to tell them to terminate (queue is FIFO)
        itemsQueue.put(None)
    
    procs = []
    # We start numUsers users processes
    for i in range(args.cores):
        procs.append(multiprocessing.Process(target=runChild, 
            args=(i, itemsQueue, resultsQueue, args.las, args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport)))
        procs[-1].start()
    
    for i in range(len(itemIds)):
        [procIndex, itemId] = resultsQueue.get()
    # wait for all users to finish their execution
    for i in range(args.cores):
        procs[i].join()
    
    # measure elapsed time
    elapsed_time = time.time() - t0    
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logging.info(msg)

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
    parser.add_argument('-c','--cores',default=1,help='Number of cores to use [default 1]',type=int, required=False)    
    return parser

if __name__ == '__main__':
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        pass
