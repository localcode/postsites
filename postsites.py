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
            'SiteProperties: {'prop0':'value0', ... }}
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

sql_root = os.path.join(os.path.abspath(__file__), 'sqls')
plpython_root  = os.path.join(os.path.abspath(__file__), 'plpython')

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
        return self.name


class Site(object):

    def __init__(self, id):
        self.id = None
        self.layers = []
        self.siteLayer = None
        self.terrainLayer = None
        self.connection = None

    def __unicode__(self):
        return 'id=%s' % self.id


class DataSource(object):

    def __init__(self, dbinfo):
        self.dbuser = dbinfo['user']
        self.dbname = dbinfo['dbname']
        self.dbpassword = ['password']
        self.dbinfo = dbinfo
        self.config = None

    def __unicode__(self):
        return 'dbname=%s' % self.dbname

    def getSiteJSON(self, id=None):
        # connect to the database
        self.connect()

        # For each layer

        for layer in self.config.layers:
            # Make a call to the database
            # use the return values to populate
            # a Layer object
            pass

        # layer and use it to build up
        # a site JSON
        siteDict = {}

        self.close()

    def viewLayers(self, filePath=None):
        if self.layer != None:
            return self.layers
        else:
            # return a list of the tables in the db
            pass

    def connect(self):
        connString = 'dbname=%s user=%s password=%s' % (self.dbname,
                self.dbuser, self.dbpassword)
        self.connection =  pg.connect(connString)
        return self.connection

    def close(self):
        self.connection.close()



if __name__=='__main__':

    # get connection info
    from configure import dbinfo

    # Make some stuff
    from layers import physical, sites
    layerDict = dict(physical.items() + sites.items())

    config = ConfigurationInfo()
    config.layers = dictToLayers(layerDict)
    config.siteLayer = 'vacantparcels'
    config.terrainLayer = 'terrain'
    config.buildingLayer = 'buildings'


    ds = DataSource(dbinfo)
    ds.config = config
    print 'site layer:', ds.config.siteLayer
    print 'terrain layer:', ds.config.terrainLayer
    print 'building layer:', ds.config.buildingLayer
    for layer in ds.config.layers:
        print layer.name

