#!/usr/bin/env python
################################################################################
#    Created by Oscar Martinez                                                 #
#            and Elena Ranguelova                                              #
#    o.rubi@esciencecenter.nl                                                  #
################################################################################
import os, argparse, time, glob, json, logging
import utils 

# CONSTANTS
DEFAULT_DB = 'vadb'

# Global variables
connection = None

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Run the script to populate the database")
    parser.add_argument('-o','--output',help='Output JSON file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=DEFAULT_DB,help='PostgreSQL DB name where to store the geometries [default ' + DEFAULT_DB + ']',type=str , required=True)
    parser.add_argument('-u','--dbuser',default=username,help='DB user [default ' + username + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=True)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=True)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=True)
    
    return parser
    
def apply_argument_parser(options=None):
    """ Apply the argument parser. """
    parser = argument_parser()
    if options is not None:
        args = parser.parse_args(options)
    else:
        args = parser.parse_args()    
    return args

def run(args):    
     t0 = time.time()
           
       
    # Global variables declaration
    global connection
    
    # Start DB connection
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    cursor.execute('select sites_pc.site_id from pc, pc_converted, sites_pc where (pc.pc_id = pc_converted.pc_id) and (pc.pc_id = sites_pc.pc_id)')
    
    rows = cursor.fetchall()
    
        
    jsonData = {}
    jsonData["type"] = "FeatureCollection"
    featuresList = []
    for row in rows:
        siteFeaturesDict = {}
        siteFeaturesDict["type"] = "Feature"
        (siteId,) = row
        cursor.execute('select site_context,site_interpretation from tbl1_site where site_id = %s', [siteId,])
        (site_context, site_interpretation) = cursor.fetchone()
        featuresList.append(siteFeaturesDict)
        
    jsonData["features"] = featuresList
    jsonData["crs"] = {}         
   
    
    
    print 'Finished!. Total time ', time.time() - t0

username = os.popen('whoami').read().replace('\n','')

if __name__ == '__main__':
    run( apply_argument_parser() )
