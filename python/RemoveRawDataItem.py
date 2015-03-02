#!/usr/bin/env python
##############################################################################
# Description:      Script to remove a raw data item and the related POTree/OSG
#
# Authors:          Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
#                   Elena Ranguelova, NLeSc
# Created:          16.02.2015
# Last modified:    02.03.2015
#
# Changes:
#
# Notes:            * User gives an ID from raw_data_item_id
#                   * The absPath of the raw data item is retrieved
#                   * The absPath of related (OSG/POTree) data item are retrieved
#                   * All the previous data is deleted
##############################################################################
import argparse
import utils, time
import shutil


logger = None
connection = None
cursor = None

def argument_parser():
    description = "Removes a Raw data item and the related converted data from the file structure."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-i', '--itemid', help='Raw data item id (with ? the available raw data items are listed)',
                        action='store', required=True)
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
 
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args() 
            
    return args
    
#def remove_data(opts):
#    """
#    Removes the data from the file structure.
#    """
#    logger.info('Removing data.')
#   # logger.info("Finished copying data to " + TARGETDIR)


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
    
#------------------------------------------------------------------------------        
def run(args): 
    
    # set logging level
    global logger
    global connection
    global cursor
    
    logger = utils.start_logging(filename=utils.LOG_FILENAME, level=args.log)
    logger.info('#######################################')
    logger.info('Starting script RemoveRawDataItem.py')
    logger.info('#######################################')

 # start timer
    t0 = utils.getCurrentTime()
    
    # connect to the DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 

    # fetch the abs_path
    abs_path = fetch_abs_path(args.itemid)        
    msg = 'Abs path fetched: %s', abs_path
    print msg
    logger.info(msg)
    
    # fetch the potree abs_paths
    abs_potree_paths, num_potree = fetch_potree_abs_paths(args.itemid)        
    msg = '%s abs potree paths fetched %s' %(num_potree, abs_potree_paths)
    print msg
    logger.info(msg)
    
    # fetch the OSG abs_paths PC
    abs_osg_pc_paths, num_osg_pc = fetch_osg_abs_paths_pc(args.itemid)        
    msg = '%s abs OSG paths for PC fetched: %s' %(num_osg_pc, abs_osg_pc_paths)
    print msg
    logger.info(msg)    

    # fetch the OSG abs_paths mesh
    abs_osg_mesh_paths, num_osg_mesh = fetch_osg_abs_paths_mesh(args.itemid)        
    msg = '%s abs OSG paths for meshes fetched: %s' %(num_osg_mesh, abs_osg_mesh_paths)
    print msg
    logger.info(msg)    
    
    # fetch the OSG abs_paths picture
    abs_osg_picture_paths, num_osg_picture = fetch_osg_abs_paths_picture(args.itemid)        
    msg = '%s abs OSG paths for pictures fetched: %s' %(num_osg_picture, abs_osg_picture_paths)
    print msg
    logger.info(msg)
    
    # fetch the OSG abs_paths PC BG
    abs_osg_pc_bg_paths, num_osg_pc_bg = fetch_osg_abs_paths_pc_bg(args.itemid)        
    msg = '%s abs OSG paths for PC BG fetched: %s' %(num_osg_pc_bg, abs_osg_pc_bg_paths)
    print msg
    logger.info(msg)
    
    # remove the files related to the above absolute paths
    shutil.rmtree(abs_path)
   
    for abs_potree_path in abs_potree_paths:
        shutil.rmtree(abs_potree_path)
   
    for abs_osg_pc_path in abs_osg_pc_paths:
        shutil.rmtree(abs_osg_pc_path)
    for abs_osg_mesh_path in abs_osg_mesh_paths:
        shutil.rmtree(abs_osg_mesh_path)
    for abs_osg_picture_path in abs_osg_picture_paths:
        shutil.rmtree(abs_osg_picture_path)
        
    for abs_osg_pc_bg_path in abs_osg_pc_bg_paths:
        shutil.rmtree(abs_osg_pc_bg_path)
    
    msg = 'Files in found abs_path locations removed!'
    print msg
    logger.info(msg)    

    # measure elapsed time
    elapsed_time = time.time() - t0    
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time, utils.LOG_FILENAME)
    print(msg)
    logger.info(msg)
    
    return


    
if __name__ == '__main__':
    run( apply_argument_parser() )
