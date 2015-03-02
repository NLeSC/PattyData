#!/usr/bin/env python
##############################################################################
# Description:      Creates a LAS/LAZ file containing the cutout of the points
#                   in the bounding box of an area delimited by the footprint 
#                   of a item/site.
# Authors:          Oscar Martinez, NLeSC, o.rubi@esciencecenter.nl
# Created:          25.02.2015
# Last modified:    25.02.2015
# Changes:
# Notes:
##############################################################################
import os, argparse, psycopg2, time, re, subprocess, glob, logging, utils

DEFAULT_CONCAVE = 0.9
DEFAULT_BUFFER = 0

def argument_parser():
    """ Define the arguments and return the parser object"""
    parser = argparse.ArgumentParser(
    description = "Creates a LAS/LAZ file containing the cutout of the points in the bounding box of an area delimited by the footprint of a item/site.\nIt is possible to specify a buffer around the footprint.\nIt also outputs an auxiliary ASCII file with the vertices of the footprint (for the z value we use the average of the z coordinates of the cutout LAS/LAZ file")
    parser.add_argument('-i','--itemid',help='Item ID',type=int, required=True)
    parser.add_argument('-o','--output',default='',help='Output LAS/LAZ file',type=str, required=True)
    parser.add_argument('-l','--las',default=utils.DEFAULT_BACKGROUND_FOLDER,help='Folder that contains the LAS/LAZ files [default ' + utils.DEFAULT_BACKGROUND_FOLDER + ']',type=str, required=False)
    parser.add_argument('-c','--concave',default=DEFAULT_CONCAVE,help='Target percentage of concavity used by PostGIS when unifying the multipolygons [default ' + str(DEFAULT_CONCAVE) + ']. Must be between 0 and 1 (1 is a convex hull)',type=type(DEFAULT_CONCAVE), required=False)    
    parser.add_argument('-d','--dbname',default=utils.DEFAULT_DB, help='PostgreSQL DB [default ' + utils.DEFAULT_DB + ']',type=str , required=False)
    parser.add_argument('-u','--dbuser',default=utils.USERNAME,help='DB user [default ' + utils.USERNAME + ']',type=str, required=False)
    parser.add_argument('-p','--dbpass',default='',help='DB pass',type=str, required=False)
    parser.add_argument('-t','--dbhost',default='',help='DB host',type=str, required=False)
    parser.add_argument('-r','--dbport',default='',help='DB port',type=str, required=False)
    parser.add_argument('-b','--buffer',default=DEFAULT_BUFFER,help='Buffer around the footprint [default ' + str(DEFAULT_BUFFER) + ']',type=type(DEFAULT_BUFFER), required=False)
    parser.add_argument('--log', help='Log level', choices=utils.LOG_LEVELS_LIST, default=utils.DEFAULT_LOG_LEVEL)
    return parser

def create_cut_out(cursor, inputLAS, output, itemid, buffer, concave):
    
    returnOk = False
    vertices = None
    avgZ = None
    numpoints = None
    
    # Make DB query to extract the bounding box of the buffer (if selected) of the concave hull of the footprint of a item/site
    # Also the concave hull is extracted
    queryDescr = 'Getting bounding box of '
    queryArgs = []
    aux = 'ch'
    if buffer > 0:
        aux = 'ST_Buffer(ch,%s)'
        queryArgs.append(buffer)
        queryDescr += 'buffer of %.2f meters around ' % buffer
    queryDescr += 'concave hull of footprint of item %s' % itemid
    query = """
SELECT 
    st_astext(ch), st_xmin(ebch), st_xmax(ebch), st_ymin(ebch), st_ymax(ebch) 
FROM (
    SELECT 
        ch, ST_Envelope(""" + aux + """) as ebch 
    FROM (
        SELECT 
            ST_ConcaveHull(geom, %s) as ch 
        FROM 
            ITEM 
        WHERE item_id = %s 
        ) A
    ) B"""
    queryArgs.extend([concave, itemid])
    logging.info(queryDescr)
    rows,num = utils.fetchDataFromDB(cursor, query, queryArgs)
    if num == 0:
        logger.error('Wrong item ID: No item is found with specified ID')
        return (returnOk, vertices, avgZ, numpoints)
    (concaveHull, minx, maxx, miny, maxy) = rows[0]
 
    # If it is found we also extract the individual 2D points of the vertices of the concave hull
    logging.info('Extracting 2D points of concave hull of footprint')
    vertices = []
    for e in concaveHull.split(','):
        c = re.findall("\d+.\d+ \d+.\d+",e)
        vertices.append(c[0].split(' '))
    
    # Check there is some LAS/LAZ file in specified directory
    listPCFiles = glob.glob(inputLAS + '/*las') + glob.glob(inputLAS + '/*laz')
    if len(listPCFiles) == 0:
        logging.error('%s does not contain any LAS/LAZ file' % inputLAS)
        return (returnOk, vertices, avgZ, numpoints)
    
    # Create list of files for lasmerge
    tfilename = output + '.list' 
    tfile = open(tfilename, 'w')
    for f in listPCFiles:
        tfile.write(f + '\n')
    tfile.close()
    command = 'lasmerge -lof ' + tfilename + ' -inside ' + str(minx) + ' ' + str(miny) + ' ' + str(maxx) + ' ' + str(maxy) + ' -o ' + output
    logging.info(command)
    os.system(command)
    os.system('rm ' + tfilename)
    if not os.path.isfile(output):
        logging.error('Output file has not been generated. Is LAStools/lasmerge installed and in PATH?')
        return (returnOk, vertices, avgZ, numpoints)
    
    logging.info('Getting average elevation and number of points from %s' % output)
    statcommand = "lasinfo -i " + output + " -nv -nmm -histo z 10000000"
    lines  = '\n'.join(subprocess.Popen(statcommand, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()).split('\n')
    
    for line in lines:
        if line.count('average z'):
             avgZ = float(line.split()[-1])
        if line.count('number of point records:'):
             numpoints = int(line.split()[-1])
    
    if numpoints == None:
        logging.error("Could not extract average elevation and number of points. Is LAStools/lasinfo installed and in PATH? Check that lasinfo in PATH is from LAStools and not libLAS!")
        return (returnOk, vertices, avgZ, numpoints)
    
    returnOk = True
    return (returnOk, vertices, avgZ, numpoints)

def run(args):
    utils.start_logging(filename=args.output + '.log', level=args.log)
    t0 = time.time()

    connection, cursor = utils.connectToDB(args.dbname, args.dbuser, args.dbpass, args.dbhost, args.dbport) 
    
    (returnOk, vertices, avgZ, numpoints) = create_cut_out(cursor, args.las, args.output, args.itemid, args.buffer, args.concave)
    
    if returnOk:
        # Create CSV with vertices of footprint
        footoutput = args.output + '_footprint.csv'
        logging.info('Creating CSV %s with vertices of concave hull of footprint' % footoutput)
        fpOutput = open(footoutput, 'w')
        for point in points:
            point.append(str(avgZ))
            fpOutput.write(','.join(point) + '\n')
        fpOutput.close()
        
        logging.info('Finished!. Time:%.2f seconds. #Points: %d' % (time.time() - t0, numpoints)) 

if __name__ == '__main__':
    run(utils.apply_argument_parser(argument_parser()))
