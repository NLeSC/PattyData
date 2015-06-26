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

logger = None
connection = None
cursor = None

def fetch_abs_path(rawDataItemId):
    """ get the absolute data item path given the rawDataItemId"""
    abs_path = ""
    
    fetch_abs_path_statement = 'select abs_path from raw_data_item where raw_data_item_id = %s'
    abs_path,num = utils.fetchDataFromDB(cursor, fetch_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_path
    
def fetch_potree_abs_paths(rawDataItemId):
    """ get the absolute data item paths for the potree converted data given the rawDataItemId"""
    abs_paths = ""
    
    fetch_potree_abs_path_statement = 'select abs_path from potree_data_item_pc natural join raw_data_item_pc where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_potree_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num   

def fetch_nexus_abs_paths(rawDataItemId):
    """ get the absolute data item paths for the nexus converted data given the rawDataItemId"""
    abs_paths = ""
    
    fetch_nexus_abs_path_statement = 'select abs_path from nexus_data_item_mesh natural join raw_data_item_pc where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_nexus_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num   
    
def fetch_osg_abs_paths_pc(rawDataItemId):
    """ get the absolute data item paths for the osg PC data given the rawDataItemId"""
    abs_paths = ""
    
    fetch_osg_abs_path_statement = 'select abs_path from osg_data_item natural join osg_data_item_pc_site where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_osg_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num   

def fetch_osg_abs_paths_mesh(rawDataItemId):
    """ get the absolute data item paths for the osg mesh data given the rawDataItemId"""
    abs_paths = ""
    
    fetch_osg_abs_path_statement = 'select abs_path from osg_data_item natural join osg_data_item_mesh where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_osg_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num   

def fetch_osg_abs_paths_picture(rawDataItemId):
    """ get the absolute data item paths for the osg picture data given the rawDataItemId"""
    abs_paths = ""
    
    fetch_osg_abs_path_statement = 'select abs_path from osg_data_item natural join osg_data_item_picture where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_osg_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num  
    
def fetch_osg_abs_paths_pc_bg(rawDataItemId):
    """ get the absolute data item paths for the osg PC data (backgrounds) given the rawDataItemID"""
    abs_paths = ""
    
    fetch_osg_abs_path_statement = 'select abs_path from osg_data_item_pc_background where raw_data_item_id = %s'
    abs_paths,num = utils.fetchDataFromDB(cursor, fetch_osg_abs_path_statement, [rawDataItemId,],[], False)
        
    
    return abs_paths, num 
    
def remove_data(abs_paths):
    """ removes all the data in the abs_paths directories"""
    for (abs_path,) in abs_paths:
        if os.path.isfile(abs_path) or os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            logger.warning('Can not remove %s. Already deleted?' % abs_path)


#------------------------------------------------------------------------------        
def run(args): 
    
    # set logging level
    global logger
    global connection
    global cursor
    
    logname = os.path.basename(__file__) + '.log'
    logger = utils.start_logging(filename=logname, level=args.log)
    localtime = utils.getCurrentTimeAsAscii()
    msg = os.path.basename(__file__) + ' script starts at %s.' % localtime
    print msg
    logger.info(msg)

     # start timer
    t0 = time.time()
    
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 

    if args.itemid == '?':
        utils.listRawDataItems(cursor)
        return
    else:
        for rawDataItemId in args.itemid.split(','):
            # fetch the abs_path
            abs_paths = fetch_abs_path(rawDataItemId)        
            msg = 'Abs path fetched: %s' % abs_paths
            print msg
            logger.info(msg)
 
            # fetch the potree abs_paths
            abs_potree_paths, num_potree = fetch_potree_abs_paths(rawDataItemId)
            msg = '%s abs potree paths fetched %s' %(num_potree, abs_potree_paths)
            print msg
            logger.info(msg)
    
            # fetch the nexus abs_paths
            abs_nexus_paths, num_nexus = fetch_nexus_abs_paths(rawDataItemId)
            msg = '%s abs nexus paths fetched %s' %(num_nexus, abs_nexus_paths)
            print msg
            logger.info(msg)
    
            # fetch the OSG abs_paths PC
            abs_osg_pc_paths, num_osg_pc = fetch_osg_abs_paths_pc(rawDataItemId)        
            msg = '%s abs OSG paths for PC fetched: %s' %(num_osg_pc, abs_osg_pc_paths)
            print msg
            logger.info(msg)    

            # fetch the OSG abs_paths mesh
            abs_osg_mesh_paths, num_osg_mesh = fetch_osg_abs_paths_mesh(rawDataItemId)        
            msg = '%s abs OSG paths for meshes fetched: %s' %(num_osg_mesh, abs_osg_mesh_paths)
            print msg
            logger.info(msg)    
    
            # fetch the OSG abs_paths picture
            abs_osg_picture_paths, num_osg_picture = fetch_osg_abs_paths_picture(rawDataItemId)        
            msg = '%s abs OSG paths for pictures fetched: %s' %(num_osg_picture, abs_osg_picture_paths)
            print msg
            logger.info(msg)
     
            # fetch the OSG abs_paths PC BG
            abs_osg_pc_bg_paths, num_osg_pc_bg = fetch_osg_abs_paths_pc_bg(rawDataItemId)        
            msg = '%s abs OSG paths for PC BG fetched: %s' %(num_osg_pc_bg, abs_osg_pc_bg_paths)
            print msg
            logger.info(msg)
    
            # remove the files related to the above absolute paths
            for abs_paths_to_remove in (abs_paths, abs_potree_paths, abs_nexus_paths, abs_osg_pc_paths, abs_osg_mesh_paths, abs_osg_picture_paths, abs_osg_pc_bg_paths):
                remove_data(abs_paths_to_remove)
    
            msg = 'Removed data locations related to raw data item %s (%s)!' % (rawDataItemId, abs_paths[0])
            print msg
            logger.info(msg)    

    # measure elapsed time
    elapsed_time = time.time() - t0
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, logname)
    print(msg)
    logger.info(msg)
    
def argument_parser():
    description = "Removes a list of Raw data items and their related converted data from the file structure."
    parser = argparse.ArgumentParser(description=description)
    # add required argument group
    requiredNamed = parser.add_argument_group('required arguments')
    # arguments
    requiredNamed.add_argument('-i', '--itemid', help='Comma-separated list of Raw Data Item Ids  Raw data item id (with ? the available raw data items are listed)',
                        action='store', required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('-l', '--log', help='Log level',
                        choices=utils.LOG_LEVELS_LIST,
                        default=utils.DEFAULT_LOG_LEVEL)
    return parser 

if __name__ == '__main__':
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
