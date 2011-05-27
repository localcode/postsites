"""
This module is intended to retrieve GeoJSON data for a particular site,
organized into layers.

Example Usage:

    >>> config = ConfigurationInfo()
    >>> config.layers = layer_dictionary
    >>> config.siteLayer = 'parcels'
    >>> config.terrainLayer = 'terrain_pts'
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

# Standard Library imports
import os

# Third party imports
import psycopg2 as pg
try: #try to import json
    import json #json is in python 2.6 and later standard libraries
except: #if json doesn't work, try simplejson
    import simplejson as json

# local package imports
import sqls

SQL_ROOT = os.path.join(os.path.abspath(__file__), 'sqls')
PLPYTHON_ROOT  = os.path.join(os.path.abspath(__file__), 'plpython')

def dictToLayers(layersDictionary):
    """
    translates a dictionary that contains information about
    site layers into a list of Layer objects.
    """
    layerList = []
    for key in layersDictionary:
        layer = Layer(layersDictionary[key]['name'])
        layer.name_in_db = key
        layer.cols = layersDictionary[key]['cols']
        if 'color' in layersDictionary[key]:
            layer.color = layersDictionary[key]['color']
        layerList.append(layer)
    return layerList

def makeLayerJSON(layer, data):
    layerDict = {'type': 'Layer', 'name':layer.name}
    geoJSONDict = {'type': 'FeatureCollection', 'features':[]}
    for row in data:
        rawJSON, columnData = row[0], row[1:]
        geomJSON = json.loads(rawJSON)
        attributeDictionary = dict(zip(layer.cols, columnData))
        featureDict = {'type':'Feature'}
        featureDict['geometry'] = geomJSON
        featureDict['properties'] = attributeDictionary
        geoJSONDict['features'].append(featureDict)
    layerDict['contents'] = geoJSONDict
    if layer.color:
        layerDict['color'] = layer.color
    return layerDict


class ConfigurationInfo(object):
    """Used to configure layers and site query parameters."""
    def __init__(self):
        self.layers = None
        self.terrainLayer = None
        self.layerDict = None
        self.siteLayer = None
        self.buildingLayer = None
        self.siteRadius = None
        self.sitePropertiesScript = None
        self.force2d = False
        self.getNearbySites = True

class Layer(object):
    """Used to hold information about individual layers."""

    def __init__(self, name):
        self.name = name
        self.name_in_db = None
        self.cols = None
        self.features = None
        self.color = None
        self.zColumn = None

    def __unicode__(self):
        return 'Layer: %s' % self.name

    def __str__(self):
        return unicode(self).encode('utf-8')


class Site(object):
    """Used to hold information about individual sites."""
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

    def _connectAndRun(self, sql):
        self._connect()
        records = self._run(sql)
        self._close()
        return records

    def _connect(self):
        connString = 'dbname=%s user=%s password=%s' % (self.dbname,
                self.dbuser, self.dbpassword)
        self.connection =  pg.connect(connString)
        return self.connection

    def _close(self):
        self.connection.close()

    def renderSQL(self, sqlTemplateName, variableDictionary,
               folder=SQL_ROOT):
        fPath = os.path.abspath(os.path.join(folder, sqlTemplateName))
        sqlString = open(fPath, 'r').read()
        for key in variableDictionary:
            sqlString.replace(('{{%s}}' % key), variableDictionary[key])
        return sqlString

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
        >>> ds = DataSource(dbinfo) # see DataSource.__doc__ about this line
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
        >>> # Or to print to a file:
        >>> tableList = ds.viewLayers("layers.py")
        >>> # Which prints each layer on a separate line
        """
        outList = []
        if self.config and self.config.layers:
            outList = self.config.layers
        else:
            self._connect()
            regexMask = '^pg_|^sql_|spatial_ref_sys|geometry_columns'
            s = "SELECT tablename FROM pg_tables WHERE tablename !~'%s';" % regexMask
            data = self._run(s)# return a list of the tables in the db
            for row in data: # data is a list of tuples
                outList.append(row[0]) #only one item in each tuple
            self._close()
        if filePath != None:
            f = open(filePath, 'w')
            f.write('\n'.join(outList))
            f.close()
            return outList
        else:
            # this could be edited to actually get the column names from the db as well
            formattedLayerDicts = [("'%s':{ 'name': '', 'cols':[ , ]}" % layer) for layer in outList]
            prefix = 'all_database_layers = {\n'
            suffix = '\n}'
            print prefix + ',\n'.join(formattedLayerDicts) + suffix
            return outList

    def getSiteJSON(self, id=None):
        # connect to the database
        self._connect()
        siteDict = {}
        siteDict["type"] = "LayerCollection"
        siteDict["layers"] = []
        # get the site layer
        if self.config.siteLayer:
            site_layer = [n for n in self.config.layers if n.name == self.config.siteLayer][0]
        # For each layer
        for layer in self.config.layers:
            #print 'Getting Layer %s from PostgreSQL' % layer.name
            if layer == site_layer: # this is the site layer
                # get the site
                siteSQL = sqls.getSite(layer.name_in_db, layer.cols,
                        id, self.config.siteRadius)
                # execute SQL
                siteData = self._run(siteSQL) # get the site
                siteJson = makeLayerJSON(layer, siteData)
                siteJson["name"] = "site"
                siteDict["layers"].append( siteJson )
                if self.config.getNearbySites:
                    # get the other sites nearby
                    otherSitesSQL = sqls.otherSites(layer.name_in_db, layer.cols,
                            id, self.config.siteRadius)
                    otherSitesData = self._run(otherSitesSQL) # get the other sites
                    if len(otherSitesData) > 0: # if there are other sites
                        otherSitesJson = makeLayerJSON(layer, otherSitesData)
                        otherSitesJson["name"] = "othersites"
                        siteDict["layers"].append( otherSitesJson )
            else: # this is some other layer
                layerSQL = sqls.getLayer(site_layer.name_in_db, layer.name_in_db,
                        layer.cols, id, self.config.siteRadius)
                layerData = self._run(layerSQL)
                if len(layerData) > 0:
                    siteDict["layers"].append(makeLayerJSON(layer, layerData))
        # close connection
        self._close()
        return json.dumps(siteDict)


if __name__=='__main__':
    import sys

    # get connection info
    from configure import dbinfo

    # get layer configuration info
    from amigos_layers import amigos_test

    # Configure the data and site parameters
    config = ConfigurationInfo()
    config.layers = dictToLayers(amigos_test)
    config.siteLayer = 'sites'
    config.siteRadius = 600

    # set up the DataSource
    ds = DataSource(dbinfo)
    # print the layers
    #tableList = ds.viewLayers() # this should print some things

    # give it the configuration
    ds.config = config
    #print '\n'.join([layer.name for layer in ds.config.layers])

    # get one Site
    #print ds.getSiteJSON(sys.argv[1])

    s = sqls.getLayer('proposed_sites', 'tinnode406', ['elevation',], 20, 100000)
    print s
    print ds._connectAndRun(s)
