#!./env/bin/python

#For debugging proposes use simple server
from wsgiref.simple_server import make_server

#For the release version use waitress
from waitress import serve
from pyramid.config import Configurator
from pyramid.response import Response
import psycopg2
import sys

#imports for multiple sessions to the DBMS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class webServer():

    def __init__(self, cloudName, user, password, host, database):
        self.cloudName = cloudName
        self.user = user
        self.password = password
        self.host = host
        self.database = database
        #To improve performance we should use sessions to load data from the PostGres server
        #Tutorial in how to create queries:
        #http://www.rmunn.com/sqlalchemy-tutorial/tutorial.html
        #self.pg_engine = create_engine('postgresql://'+self.user+':'+self.database'@'+self.host+'/')
        #Session = sessionmaker(bind=pg_engine)
        #self.session = Session()


    def set_up(self):
        # Set up
        self.connection = psycopg2.connect(database=self.database, user=self.user, password=self.password)
        self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.connection.cursor()

    def get_nodeB(self, request):
        name = request.matchdict ['name']
        form = request.matchdict ['form']
        pc = request.matchdict ['pc']
        self.cursor.execute("SELECT octreeName FROM " + self.cloudName + " WHERE area = 'BACKGROUND' and form = '" + form + "' and pc = '" + pc + "';")
        result = self.cursor.fetchone()
        octreeName= result[0]
        self.cursor.execute("SELECT data FROM " + octreeName + " WHERE nodename = '" + name + "';")
        result = self.cursor.fetchone()
        data = result[0]
        response = Response()
        headers = response.headers
        headers['Accept-Ranges'] = 'bytes'
        #headers['Content-Type'] = 'application/zip'
        #headers['Type'] = 'application/octet-stream'
        headers['Content-Type'] = 'application/octet-stream'
        headers['Size'] = str(len(data))
        response.app_iter = data
        return response

    def get_nodeS(self, request):
        name = request.matchdict ['name']
        siteNum = request.matchdict ['siteNum']
        form = request.matchdict ['form']
        pc = request.matchdict ['pc']
        self.cursor.execute("SELECT octreeName FROM " + self.cloudName + " WHERE area = 'SITES' and form = '" + form + "' and pc = '" + pc + "' and siteNum = '" + siteNum +"';")
        result = self.cursor.fetchone()
        octreeName=result[0]
        self.cursor.execute("SELECT data FROM " + octreeName + " WHERE nodename = '" + name + "';")
        result = self.cursor.fetchone()
        data = result[0]
        response = Response()
        headers = response.headers
        headers['Accept-Ranges'] = 'bytes'
        #headers['Content-Type'] = 'application/zip'
        #headers['Type'] = 'application/octet-stream'
        headers['Content-Type'] = 'application/octet-stream'
        headers['Size'] = str(len(data))
        response.app_iter = data
        return response

    def get_confB(self, request):
        form = request.matchdict ['form']
        pc = request.matchdict ['pc']
        self.cursor.execute("SELECT data FROM " + self.cloudName + " WHERE area = 'BACKGROUND' and form = '" + form + "' and pc = '" + pc + "';")
        result = self.cursor.fetchone()
        data = result[0]
        response = Response()
        headers = response.headers
        headers['Accept-Ranges'] = 'bytes'
        headers['Content-Type'] = 'application/json'
        headers['Size'] = str(len(data))
        response.app_iter = data
        return response

    def get_confS(self, request):
        siteNum = request.matchdict ['siteNum']
        form = request.matchdict ['form']
        pc = request.matchdict ['pc']
        self.cursor.execute("SELECT data FROM " + self.cloudName + " WHERE area = 'SITES' and form = '" + form + "' and pc = '" + pc + "' and siteNum = '" + siteNum + "';")
        data = result[0]
        response = Response()
        headers = response.headers
        headers['Accept-Ranges'] = 'bytes'
        headers['Content-Type'] = 'application/json'
        headers['Size'] = str(len(data))
        response.app_iter = data
        return response

if __name__ == '__main__':
    config = Configurator()
    cloudName = 'cloud'
    user = 'romulog'
    password = 'romulog'
    host = 'localhost'
    database = 'demo'
    webServer = webServer(cloudName, user, password, host, database)
    webServer.set_up()
    
    #Get conf for Background
    config.add_route('confB', '/BACKGROUND/{form}/{pc}/cloud.js')
    config.add_view(webServer.get_confB, route_name='confB')

    #Get octree nodes for Background
    config.add_route('nodeB', '/BACKGROUND/{form}/{pc}/data/{name}')
    config.add_view(webServer.get_nodeB, route_name='nodeB')

    #Get octree nodes for Sites
    config.add_route('nodeS', '/SITES/{siteNum}/PC/{form}/{pc}/data/{name}')
    config.add_view(webServer.get_nodeS, route_name='nodeS')

    #Get conf for SITES
    config.add_route('confS', '/SITES/{siteNum}/PC/{form}/{pc}/cloud.js')
    config.add_view(webServer.get_confS, route_name='confS')

    app = config.make_wsgi_app()
    #For debugging proposes use simple server
    #server = make_server('0.0.0.0', 8090, app)

    #For the release version use waitress
    server = serve(app, host='0.0.0.0', port=8090)
    server.serve_forever()


