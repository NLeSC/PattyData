#!/usr/bin/python

import sys
import getopt
import string
import psycopg2
import json
from pprint import pprint

class connectToPostGres():

    def __init__(self, area, form, pc, siteNum, cloudFileName, dataPathName, user, password, host, database):
        self.area = area
        self.form = form
        self.pc = pc
        self.siteNum = siteNum
        self.cloudFileName = cloudFileName
        self.dataPathName = dataPathName
        self.user = user
        self.password = password
        self.host = host
        self.database = database

    def set_up(self):
        # Set up
        self.connection = psycopg2.connect(database=self.database, user=self.user, password=self.password)
        self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.connection.cursor()

    def parseJson(self):
        json_data=open(self.cloudFileName)
        self.data = json.load(json_data)
        json_data.close()
        self.fileType = self.data["pointAttributes"]

    def loadCloud(self):
        lx = str(self.data["boundingBox"]["lx"]) 
        ly = str(self.data["boundingBox"]["ly"]) 
        lz = str(self.data["boundingBox"]["lz"]) 
        ux = str(self.data["boundingBox"]["ux"]) 
        uy = str(self.data["boundingBox"]["uy"]) 
        uz = str(self.data["boundingBox"]["uz"]) 
        inFormat = self.data["pointAttributes"] 
        spacing = self.data["spacing"] 

        self.cursor.execute("SELECT count(*) as rowCount FROM cloud;")
        result = self.cursor.fetchone()
        self.octreeName="octree" + str(result[0])
        fileFP = open(self.cloudFileName, 'rb')
        filedata = psycopg2.Binary( fileFP.read() )
        self.cursor.execute("insert into cloud (area, form, pc, siteNum, lx, ly, lz, ux, uy, uz, spacing, format, octreeName, data) values ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", 
            (self.area, self.form, self.pc, self.siteNum, lx, ly, lz, ux, uy, uz, spacing, inFormat, self.octreeName, filedata));
        self.connection.commit()

    def loadOctree(self):
        self.cursor.execute("CREATE TABLE " + self.octreeName + " (nodename varchar(32), npoints int, data bytea);")
        self.connection.commit()
        fileList = self.data["hierarchy"]
        for f in fileList:
            filename = f[0]
            if (self.fileType == "LAZ"):
                filename = filename + '.laz'
            if (self.fileType == "LAS"):
                filename = filename + '.las'
            fileFP = open(self.dataPathName + filename, 'rb')
            filedata = psycopg2.Binary( fileFP.read() )
            self.cursor.execute("insert into " + self.octreeName + " (nodename, npoints, data) values (%s, %s, %s);", (filename, f[1], filedata))
            fileFP.close()
            self.connection.commit()

    def queryCloud(self):
        query = self.cursor.execute('SELECT * FROM cloud;');
        result = self.cursor.fetchall()
        print "Cloud contains the following octrees:", result

    def queryOctree(self):
        f = open('test.out','wb')
        self.cursor.execute("SELECT nodename, npoints, data FROM " + self.octreeName + " LIMIT 1;")
        (nodename, npoints, data) = self.cursor.fetchone()

        print "First node from the Octree:", (nodename, npoints)
        f.write(data)
        f.close()

    def close(self):
        self.cursor.close()
        self.connection.close()


def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)

    # process options
    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            sys.exit(0)

    # process arguments
    area = 'BACKGROUND'
    form = 'CONV'
    pc = 'pc1'
    siteNum = 'null'
    cloudFileName = '/home/romulog/NLeSc/gitHub/patty/PattyVis/BACKGROUND/CONV/pc1/cloud.js'
    dataPathName = '/home/romulog/NLeSc/gitHub/patty/PattyVis/BACKGROUND/CONV/pc1/data/'
    user = 'romulog'
    password = 'romulog'
    host = 'localhost'
    database = 'demo'
    #for arg in args:
        #process(arg) # process() is defined elsewhere
                                                                                          
    test = connectToPostGres(area, form, pc, siteNum, cloudFileName, dataPathName, user, password, host, database)
    test.set_up()
    test.parseJson()
    test.loadCloud()
    test.queryCloud()
    test.loadOctree()
    test.queryOctree()
    test.close()

if __name__ == "__main__":
    main()
