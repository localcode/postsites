"""
This module is intended to retrieve GeoJSON data for a particular site,
organized into layers.

Example Usage:

    >>> config = ConfigurationInfo()
    >>> config.layers = layer_dictionary
    >>> config.siteLayer = 'parcels'
    >>> config.terrainLayer = 'terrain_pts'
    >>> config.sitePropertiesScript = 'myscript.py'
    >>> config.distance = 100
    >>> ds = DataSource(dbinfo)
    >>> ds.configure(config)
    >>> ds.getSiteJSON( id=200 )
    {'Layers':[{'layer':'site', {'type':'Feature', 'geometry': {...}, 'properties':{...}}},
            {'layer':'terrain', {'type':'FeatureCollection':[ ... ]}},
            {'layer':'othersites', 'FeatureCollection':[ ... ]},
            {'layer':'buildings', 'FeatureCollection':[ ... ]}],
            'SiteProperties': {'prop0':'value0', ... }}
    >>> ds.getSite( id=190 )
    <Site object:'site 190'>
    >>> s = Site(ds, id=200)
    >>> s2 = Site(ds, query='assess_val = 3000')
    >>> s.properties
    None
    >>> s.build() # retrieves the site data and builds
    >>> s.properties
    {'prop0':'value0', ... }
    >>> s.layers
    [<Layer object:'terrain'>, <Layer object:'buildings'>, ... ]
    >>> s.prop0
    'value0'
    >>> layer = s.layers[2]
    >>> layer.features
    {'FeatureCollection':[ ... ]}

"""

import os
import psycopg2 as pg
import simplejson as json

SQL_ROOT = os.path.join(os.path.abspath(__file__), 'sqls')
PLPYTHON_ROOT  = os.path.join(os.path.abspath(__file__), 'plpython')

def dictToLayers(layerDictionary):
    layerList = []
    for key in layerDictionary:
        layer = Layer(key)
        layer.name_in_db = layerDictionary[key][0]
        layer.cols = layerDictionary[key][1:]
        layerList.append(layer)
    return layerList


class ConfigurationInfo(object):

    def __init__(self):
        self.layers = None
        self.terrainLayer = None
        self.layerDict = None
        self.siteLayer = None
        self.buildingLayer = None
        self.siteRadius = None
        self.sitePropertiesScript = None

class Layer(object):

    def __init__(self, name):
        self.name = name
        self.name_in_db = None
        self.cols = None
        self.features = None

    def __unicode__(self):
        return 'Layer: %s' % self.name

    def __str__(self):
        return unicode(self).encode('utf-8')


class Site(object):

    def __init__(self, id):
        self.id = None
        self.layers = []
        self.siteLayer = None
        self.terrainLayer = None
        self.connection = None

    def __unicode__(self):
        return 'Site: id=%s' % self.id

    def __str__(self):
        return unicode(self).encode('utf-8')


class DataSource(object):
    """
    Represents a connection to a PostGIS database.
    Holds database connection information and runs
    queries to the databse, using the psycopg2 advice
    that creating separate cursors is cheap, while
    making separate connections is expensive.
    Should be initialized with a dictionary containing
    database connection information:
    >>> dbinfo = {'user':'me','dbname':'mydb','password':'pa55w0rd'}
    >>> ds = DataSource(dbinfo)
    >>> print ds
    DataSource: dbname=mydb
    """

    def __init__(self, dbinfo):
        self.dbuser = dbinfo['user']
        self.dbname = dbinfo['dbname']
        self.dbpassword = dbinfo['password']
        self.dbinfo = dbinfo
        self.config = None
        self.connection = None

    def __unicode__(self):
        return 'DataSource: dbname=%s' % self.dbname

    def __str__(self):
        return unicode(self).encode('utf-8')

    def _run(self, sql):
        cur = self.connection.cursor()
        cur.execute(sql)
        records = cur.fetchall()
        cur.close()
        return records

    def connect(self):
        connString = 'dbname=%s user=%s password=%s' % (self.dbname,
                self.dbuser, self.dbpassword)
        self.connection =  pg.connect(connString)
        return self.connection

    def close(self):
        self.connection.close()

    def renderSQL(self, sqlTemplateName, variableDictionary,
               folder=SQL_ROOT):
        fPath = os.path.abspath(os.path.join(folder, sqlTemplateName))
        sqlString = open(fPath, 'r').read()
        for key in variableDictionary:
            sqlString.replace(('{{%s}}' % key), variableDictionary[key])
        return sqlString

    def getSiteJSON(self, id=None):
        # connect to the database
        self.connect()

        siteDict = {}

        # For each layer
        for layer in self.config.layers:
            # make a dictionary for the layer
            renderDict = {
                    'table':layer.name,
                    'id':id,
                    'cols':', '.join(layer.cols)
                    }
            # render the sql
            layerSQL = self.renderSQL('getLayer.sql', renderDict)
            # get the data
            results = self._run(layerSQL)
            # the data should be a set of tuples

            # put the data into the site dictionary
            siteDict[layer.name] = results

        # close connection
        self.close()

        return siteDict

    def viewLayers(self, filePath=None):
        """
        prints a list of configured layers or tables in the database
        if the DataSource already has configured layers, viewLayers()
        will simply print and return the list of layers. If no layers
        have been configured, then viewLayers will print a list of
        every table in the databse, for the purpose of configuring
        them. A file path can be passed to viewLayers to write the
        list to a file.
        Example:
        >>> ds = DataSource(dbinfo) # see Datasource doc about this line
        >>> tableList = ds.viewLayers()
        tgr06037elm
        spatial_ref_sys
        geometry_columns
        tgr06037lkf
        floodmaintbdy
        laco_parks
        dpw_smd_nosmd_pp
        hydro3000feetbuffer
        garbagedisposaldist
        >>> tableList
        ['tgr06037elm', 'spatial_ref_sys', 'geometry_columns', 'tgr06037lkf', 'floodmaintbdy', 'laco_parks', 'dpw_smd_nosmd_pp', 'hydro3000feetbuffer', 'garbagedisposaldist']

        Or to print to a file:
        >>> tableList = ds.viewLayers("layers.py")
        Which prints each layer on a separate line
        """
        outList = []
        if self.config and self.config.layers:
            outList = self.config.layers
        else:
            self.connect()
            s = "SELECT tablename FROM pg_tables WHERE tablename !~'^pg_|^sql_';"
            data = self._run(s)# return a list of the tables in the db
            for row in data: # data is a list of tuples
                outList.append(row[0]) #only one item in each tuple
            self.close()
        if filePath != None:
            f = open(filePath, 'w')
            for table in outList:
                f.write(str(table))
            f.close()
            return outList
        else:
            for layer in outList:
                print layer
            return outList


if __name__=='__main__':

    # get connection info
    from configure import dbinfo

    # Make some stuff
    from layers import physical, sites
    layerDict = dict(physical.items() + sites.items())

    config = ConfigurationInfo()
    config.layers = dictToLayers(layerDict)


    ds = DataSource(dbinfo)
    layers = ds.viewLayers()
    print layers
    #ds.config = config
    #print 'site layer:', ds.config.siteLayer
    #print 'terrain layer:', ds.config.terrainLayer
    #print 'building layer:', ds.config.buildingLayer
    #for layer in ds.config.layers:
        #print layer
        #print layer.name, layer.name_in_db, layer.cols
        #print

    #print ds.getSiteJSON(id=200)
