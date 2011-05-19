"""
This module is intended to retrieve GeoJSON data for a particular site,
organized into layers.
"""
import os
import psycopg2 as pg

sql_root = os.path.join(os.path.abspath(__file__), 'sqls')
plpython_root  = os.path.join(os.path.abspath(__file__), 'plpython')

class ConfigurationInfo(object):

    def __init__(self):
        self.layers = None
        self.terrainLayer = None
        self.layerDict = None
        self.siteLayer = None
        self.siteRadius = None
        self.sitePropertiesScript = None


class Layer(object):

    def __init__(self, name):
        self.name = name
        self.features = None


class Site(object):

    def __init__(self, id):
        self.id = None
        self.layers = []
        self.siteLayer = None
        self.terrainLayer = None


class DataSource(object):

    def __init__(self, dbinfo):
        self.dbuser = dbinfo['user']
        self.dbname = dbinfo['dbname']
        self.dbpassword = ['password']
        self.dbinfo = dbinfo
        self.layers = None

    def getSiteJSON(self, id=None):
        # For each layer
        for layer in layers:
            # Make a call to the database
            # use the return values to populate
            # a Layer object
            pass

        # layer and use it to build up
        # a site dictionary
        siteDict = {}

        pass

    def viewLayers(self, filePath=None):
        if self.layer != None:
            return self.layers
        else:
            # return a list of the tables in the db
            pass







def test():
    """
    This is hard to conceptualize, but I've already done it.
    Let's try to whip up some imagined usage examples and build from there.

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

if __name__=='__main__':

    # Make some stuff
    from layers import physical, sites
    layerDict = dict(physical.items() + sites.items())

    config = ConfigurationInfo()
    config.layers = layerDict
    config.siteLayer = 'vacantparcels'
    config.terrainLayer = 'terrain'




