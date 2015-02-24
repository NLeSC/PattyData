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
import os, argparse, utils, time, logging, psycopg2

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
    parser.add_argument('--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    return parser

def run(args):
    utils.start_logging(filename=args.input + '.log', level=args.log)

    t0 = utils.getCurrentTime()

    logging.info('Checking validity of SQL file')
    # Check that beginning of the file does not contain a create database statement
    if os.popen('head -500 ' + args.input + ' | grep "CREATE DATABASE"').read().count("CREATE DATABASE"):
        logging.error("You must remove CREATE DATABASE statement from the SQL file")
        return
    # Check that ther are not defaults in TIMESTAMPS that would cause errors
    if os.popen('grep "TIMESTAMP DEFAULT" ' + args.input).read().count("TIMESTAMP DEFAULT"):
        logging.error("You must remove any DEFAULT value of any TIMESTAMP column")
        return
    # Check that ther are not index creations
    if os.popen('grep "INDEX" ' + args.input).read().count("INDEX"):
        logging.error("You must remove any INDEX creation")
        return
    if os.popen("""grep '"' """ + args.input).read().count('"'):
        logging.error('You must remove any double quote (")')
        return
    
    # Establish connection with DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 
    
    # First we need to drop the previous constraints in tbl1_site and tbl1_object
    logging.info("Dropping constraints in tbl1_site and tbl1_object tables")
    for tablename in ('tbl1_site','tbl1_object'):
        cursor.execute("select constraint_name from information_schema.table_constraints where table_name=%s", [tablename,])
        constraintNames = cursor.fetchall()
        for (constraintName, ) in constraintNames:
            cursor.execute('ALTER TABLE ' + tablename + ' DROP CONSTRAINT ' + constraintName)
            connection.commit()
    
    # This script will drop all attribute tables and create them again
    logging.info('Executing SQL file %s' % args.input)
    utils.load_sql_file(cursor, args.input)
    
    # Set select permissions to all new tables
    logging.info('Granting select permissions to all tables')
    cursor.execute("select tablename from  pg_tables where schemaname = 'public'")
    tablesNames = cursor.fetchall()
    for (tableName,) in tablesNames:
        cursor.execute('GRANT SELECT ON ' + tableName + ' TO public')

    # We check that the added Sites and Objects are also in Data Management part of the DB
    # All sites in tbl1_site must have an entry in ITEM
    logging.info('Adding items in attribute data that are missing in ITEM table')
    query = 'SELECT site_id from tbl1_site WHERE site_id NOT IN (SELECT item_id FROM item)'
    sites, num_sites = utils.fetchDataFromDB(cursor, query)
    for (siteId, ) in sites:
        utils.dbExecute(cursor, "INSERT INTO ITEM (item_id, background) VALUES (%s,%s)", [siteId, False])
        utils.dbExecute(cursor, "INSERT INTO ITEM_OBJECT (item_id, object_number) VALUES (%s,%s)", [siteId, utils.ITEM_OBJECT_NUMBER_ITEM])
    
    # All objects in tbl1_object must also be in ITEM_OBJECT
    logging.info('Adding items objects in attribute data that are missing in ITEM_OBJECT table')
    query = 'SELECT site_id,object_id from tbl1_site WHERE (site_id,object_id) NOT IN (SELECT item_id,object_number FROM item_object)'
    sites_objects, num_sites_objects = utils.fetchDataFromDB(cursor, query)
    for (siteId, objectId) in sites:
        utils.dbExecute(cursor, "INSERT INTO ITEM_OBJECT (item_id, object_number) VALUES (%s,%s)", [siteId, objectId])
                
    #We add again the constraints that link management and attribute data
    logging.info('Adding constraints between attribute and items')
    cursor.execute("""ALTER TABLE tbl1_object
ADD FOREIGN KEY (site_id, object_id)
REFERENCES ITEM_OBJECT (item_id, object_number)
ON UPDATE NO ACTION
ON DELETE NO ACTION""")
    connection.commit()
    cursor.execute("""ALTER TABLE tbl1_site
ADD FOREIGN KEY (site_id)
REFERENCES ITEM (item_id)
ON UPDATE NO ACTION
ON DELETE NO ACTION""")
    connection.commit()
    
    elapsed_time = utils.getCurrentTime() - t0    
    msg = 'Finished. Total elapsed time: %s s.' %elapsed_time
    print(msg)
    logging.info(msg)

if __name__ == '__main__':
    run(utils.apply_argument_parser(argument_parser()))

