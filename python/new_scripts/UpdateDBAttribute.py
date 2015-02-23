#!/usr/bin/env python
################################################################################
# Description:      Update the Attribute part of the DB from a Microsoft Access 
#                   dump. Remove previous content in the part.
# Author:           Oscar Martinez Rubi, NLeSc, O.rubi@nlesc.nl                                       
# Creation date:    23.02.2015      
# Modification date: 23.02.2015
# Modifications:   
# Notes:            
################################################################################
import os, argparse, utils, time, re, multiprocessing, glob, logging, shutil
import psycopg2

logger = None
connection = None
cursor = None

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Merges AccessDB file with ViaAppia DB (it requires to have converted Access file into SQL dump")
    parser.add_argument('-i','--input',help='SQL file with dumped Microsoft Access file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name which should be updated with the attribute data ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=True)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=True)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=True)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    return parser


def addSiteObject(cursor, siteId, objectNumber):
    (x,y)=(0,0)
    proto = utils.DEFAULT_PROTO
    position = utils.getPositionFromFootprint(cursor, siteId)
    if position != None:
        (x,y) = position
        utils.addSiteObject(cursor, siteId, objectNumber, proto, x, y)
        
def main(opts):
    # Check that beginning of the file does not contain a create database statement
    if os.popen('head -500 ' + opts.input + ' | grep "CREATE DATABASE"').read().count("CREATE DATABASE"):
        logging.error("You must remove CREATE DATABASE statement from the SQL file")
        return
    # Check that ther are not defaults in TIMESTAMPS that would cause errors
    if os.popen('grep "TIMESTAMP DEFAULT" ' + opts.input).read().count("TIMESTAMP DEFAULT"):
        logging.error("You must remove any DEFAULT value of any TIMESTAMP column")
        return
    # Check that ther are not index creations
    if os.popen('grep "INDEX" ' + opts.input).read().count("INDEX"):
        logging.error("You must remove any INDEX creation")
        return
    if os.popen("""grep '"' """ + opts.input).read().count('"'):
        logging.error('You must remove any double quote (")')
        return
    
     
    # Establish connection with DB
    connection = psycopg2.connect(utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, False))
    cursor = connection.cursor()
    
    # First we need to drop the previous constraints in tbl1_site and tbl1_object
    for tablename in ('tbl1_site','tbl1_object'):
        cursor.execute("select constraint_name from information_schema.table_constraints where table_name=%s", [tablename,])
        constraintNames = cursor.fetchall()
        for (constraintName, ) in constraintNames:
            cursor.execute('ALTER TABLE ' + tablename + ' DROP CONSTRAINT ' + constraintName)
            connection.commit()
    
    # We load the new file
    connParams = utils.postgresConnectString(opts.dbname, opts.dbuser, opts.dbpass, opts.dbhost, opts.dbport, True)
    logFile = opts.input + '.log'
    command = 'psql ' + connParams + ' -f ' + opts.input + ' &> ' + logFile
    logging.info(command)
    os.system(command)
    
    #Check errors
    if os.popen('cat ' + logFile + ' | grep ERROR').read().count("ERROR"):
        logging.error('There was some errors in the data loading. Please see log ' + logFile)
    else:
        cursor.execute("select tablename from  pg_tables where schemaname = 'public'")
        tablesNames = cursor.fetchall()
        for (tableName,) in tablesNames:
            utils.dbExecute(cursor, 'GRANT SELECT ON ' + tableName + ' TO public')
        
        for tableName in ('active_objects_sites_objects','boundings','active_objects_labels','cameras'):
            utils.dbExecute(cursor, 'GRANT SELECT,INSERT,UPDATE,DELETE ON ' + tableName + ' TO public')
 
        # We check that the added Sites and Objects are also in Data Management part of the DB
        # All the sites must have a objects which ID = -1 that it is the site itself
        # We add the missing one
        utils.dbExecute(cursor, 'SELECT site_id FROM ((SELECT distinct site_id from tbl1_site) UNION (SELECT distinct site_id from active_objects_sites) UNION (SELECT distinct site_id from sites_geoms)) A WHERE site_id not in (SELECT site_id from active_objects_sites_objects WHERE object_id = %s)', [utils.SITE_OBJECT_NUMBER])
        rows = cursor.fetchall()
        for row in rows:
            addSiteObject(cursor, row[0], utils.SITE_OBJECT_NUMBER)
        # Add missing objects
        utils.dbExecute(cursor, 'SELECT site_id,object_id from tbl1_object WHERE (site_id,object_id) NOT IN (SELECT site_id,object_id from active_objects_sites_objects)')
        rows = cursor.fetchall()
        for row in rows:
            addSiteObject(cursor, row[0], row[1])
            
        # Warn of objects in sites_objects which are not in access db part
        utils.dbExecute(cursor, 'SELECT site_id,object_id from active_objects_sites_objects WHERE object_id != %s and (site_id,object_id) NOT IN (SELECT site_id,object_id from tbl1_object)', [utils.SITE_OBJECT_NUMBER,])
        rows = cursor.fetchall()
        for (siteId, objectId) in rows:
            logging.warn("Site " + str(siteId) + " object " + str(objectId) + " is in active_obejcts_sites_objects but not in tbl1_object")
            
        #We add again the constraints that link managmeent and attribute data
        cursor.execute("""ALTER TABLE tbl1_object
    ADD FOREIGN KEY (site_id, object_id)
    REFERENCES ACTIVE_OBJECTS_SITES_OBJECTS (site_id, object_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION""")
        connection.commit()
        cursor.execute("""ALTER TABLE tbl1_site
    ADD FOREIGN KEY (site_id)
    REFERENCES SITES_GEOMS (site_id)
    ON UPDATE NO ACTION
    ON DELETE NO ACTION""")
        connection.commit()

if __name__ == '__main__':
    run(utils.apply_argument_parser(argument_parser()))

