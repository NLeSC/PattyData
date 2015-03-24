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

def run(args):
    logname = os.path.basename(args.input) + '.log'
    utils.start_logging(filename=logname, level=args.log)
    
    localtime = utils.getCurrentTimeAsAscii()
    t0 = time.time()
    msg = os.path.basename(__file__) + ' script starts at %s.' %localtime
    print msg
    logging.info(msg)

    logging.info('Checking validity of SQL file')
    # Check that beginning of the file does not contain a create database statement
    if os.popen('head -500 ' + args.input + ' | grep "CREATE DATABASE"').read().count("CREATE DATABASE"):
        msg = "You must remove CREATE DATABASE statement from the SQL file"
        print msg
        logging.error(msg)
        return
    # Check that ther are not defaults in TIMESTAMPS that would cause errors
    if os.popen('grep "TIMESTAMP DEFAULT" ' + args.input).read().count("TIMESTAMP DEFAULT"):
        msg = "You must remove any DEFAULT value of any TIMESTAMP column"
        print msg
        logging.error(msg)
        return
    # Check that ther are not index creations
    if os.popen('grep "INDEX" ' + args.input).read().count("INDEX"):
        msg = "You must remove any INDEX creation"
        print msg
        logging.error(msg)
        return
    if os.popen("""grep '"' """ + args.input).read().count('"'):
        msg ='You must remove any double quote (")'
        print msg
        logging.error(msg)
        dangerousWords = []
        for line in open(args.input,'r').read().split('\n'):
            if not line.startswith('--'):
                for word in line.split():
                    if word.count('"') == 1:
                        dangerousWords.append(word)
        if len(dangerousWords):
            msg = 'Also, before removing all ", take care of table and column names that would be incorrect when removing ".\n If any of the following is a table or column name please be sure that it does not have white spaces: ' + ','.join(dangerousWords)
            print msg
            logging.error(msg)
            return
        return
    
    # Establish connection with DB
    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 
      
    # First we drop all tables in attribute
    logging.info("Dropping all previous attribute tables")
    for tablename in ('tbl2_site_relation','tbl2_object_depression','tbl2_object_decoration','tbl2_object_material','tbl1_object','tbl1_site'):
        cursor.execute('DROP TABLE IF EXISTS ' + tablename + ' CASCADE')
        connection.commit()
    # First we need to drop the previous constraints in tbl1_site and tbl1_object
#    logging.info("Dropping constraints in tbl1_site and tbl1_object tables")
#    for tablename in ('tbl1_site','tbl1_object'):
#        cursor.execute("select constraint_name from information_schema.table_constraints where table_name=%s", [tablename,])
#        constraintNames = cursor.fetchall()
#        for (constraintName, ) in constraintNames:
#            cursor.execute('ALTER TABLE ' + tablename + ' DROP CONSTRAINT %s CASCADE', [constraintName,])
#            connection.commit()
    
    # This script will drop all attribute tables and create them again
    logging.info('Executing SQL file %s' % args.input)
    #utils.load_sql_file(cursor, args.input)
    connParams = utils.postgresConnectString(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport, True)
    logFile = os.path.basename(args.input) + '.log'
    command = 'psql ' + connParams + ' -f ' + args.input + ' &> ' + logFile
    logging.info(command)
    os.system(command)
    
    #Check errors
    if os.popen('cat ' + logFile + ' | grep ERROR').read().count("ERROR"):
        msg = 'There was some errors in the data loading. Please see log ' + logFile
        print msg
        logging.error(msg)
        return
    
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
    query = 'SELECT site_id,object_id from tbl1_object WHERE (site_id,object_id) NOT IN (SELECT item_id,object_number FROM item_object)'
    sites_objects, num_sites_objects = utils.fetchDataFromDB(cursor, query)
    for (siteId, objectId) in sites_objects:
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
    
    elapsed_time = time.time() - t0    
    msg = 'Finished. Total elapsed time: %.02f seconds. See %s' % (elapsed_time,logname)
    print(msg)
    logging.info(msg)


def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description="Merges AccessDB file with ViaAppia DB (it requires to have converted Access file into SQL dump")
    parser.add_argument('-i','--input',help='SQL file with dumped Microsoft Access file',type=str, required=True)
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB name which should be updated with the attribute data ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    return parser


if __name__ == '__main__':
    try:
        utils.checkSuperUser()
        run(utils.apply_argument_parser(argument_parser()))
    except Exception as e:
        print e
    

