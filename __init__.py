"""
This module is meant to make the process of loading a bunch of shapefiles and
then retrieving data on a per-site basis as painless as possible.
The target audience for PostSites is amateur programmers/designers who are
using scripts in 3d modeling programs or web stuff to import GIS data
in GeoJSON format (a nice, readable, easy to parse format for GIS data that
supports 3D). The package includes utilities that make it easy to load a large
set of shapefiles into a PostGIS database, as well as classes that aid in configuring
how site information is retrieved from that database. This module is intended to retrieve
GeoJSON data for a particular site, organized into a set of layers.

Dependencies:
    PostSites is intended to work with PostGIS (hence the name), and
    therefore expects that a PostGIS database is available, and that both
    PostgreSQL and PostSites are installed. To make calls to the databse,
    it uses psycopg2, and if using python 2.5 or earlier, it needs simplejson
    as well. Additionally, it uses ogr2ogr and ogrinfo, commandline utilities included
    with GDAL for loading and reading data. There are a couple of configuraiton and loading
    scripts that utilize xlwt and xlrd. PostSites should work equally well on Windows
    or Mac.

Examples (disclaimer: still in development)

First, we'll designate a folder that contains our shapefiles. PostSites will detect
any shapefiles that inside this folder, even if they are nested into other folders.

    >>> my_data_folder = 'C:\Users\myusername\Desktop\GIS data'

The next command is a utility that makes it easy to configure how
our shapefiles are loaded into the PostGIS database.
It gives you one spreadsheet with all unique spatial reference systems
and another sheet that lets you configure information about each file
as well as letting you define any unknown projections. See the tutorials for
examples of how to edit this file.

    >>> import postsites
    >>> f = postsites.makeXlsConfigurationFile(my_data_folder)
    >>> f
    'xls_config_GIS_data.xls' # the name of the resulting file.

Once you have edited the 'xls_config_GIS_data.xls' file, you can use it to load
everything into the database ...

    >>> dbinfo = {'user':'me', 'dbname':'mydb', 'password':'s3cr3TP455w0rdZ'} # this is needed to connect to the db
    >>> ds = postsites.loadFromXlsConfigurationFile( f, dbinfo ) # this may take a while, go get a coffee
    >>> ds # ds is a DataSource object that we can use to retrieve and configure site information.
    <postsites.DataSource object>

Next, we can start getting JSON data for a site like this:

    >>> mysiteJson = ds.getSiteJson(id=203)

"""

# Standard Library imports
import os

# Third party imports
import psycopg2 as pg
try: #try to import json
    import json #json is in python 2.6 and later standard libraries
except: #if json doesn't work, try simplejson
    import simplejson as json

try:
    import numpy as np
    import scipy.spatial.qhull as qhull
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

# local package imports
import loader
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

def makeTerrainJSON(layer, terrainData):
    # this should create a different json type. How about
    # 'MESH'? It will also need to iterate through the
    # geometry and take out Zs and triangulate
    if not HAS_SCIPY:
        print '''NumPy and SciPy must be installed in order to triangulate
        terrain. Please ensure that both are installed and available on
        sys.path.'''
        return
    from triforce import triangulate
    layerDict = {'type': 'Layer', 'name':layer.name}
    geoJSONDict = {'type': 'FeatureCollection', 'features':[]}
    points2d = []
    pointZs = []
    pointAttributes = [] # a list of attribute values for each point
    for row in terrainData: # each row will contain a point
        rawJSON, columnData = row[0], row[1:]
        geomJSON = json.loads(rawJSON)
        # here is where I should triangulate it.
        point = geomJSON['coordinates']
        point2d, pointZ = [point[0], point[1]], point[2]
        points2d.append(point2d)
        pointZs.append(pointZ)
        # this creates one list for each point
        pointAttributes.append(columnData)
    # now triangulate the points2d
    tris = triangulate(points2d)
    geomJSON = {'type': 'Mesh'} # a new geoJSON type!
    geomJSON['coordinates'] = points
    geomJSON['faces'] = tris
    transposedAttributes = zip(*pointAttributes) #omg hack!
    attributeDictionary = dict(zip(layer.cols, transposedAttributes)) # I think this should work
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
        self.layerLoadResults = None # store results from loading operations
        # results should store ( layer, loaded:True/False, result message )
        self.terrainLayer = None
        self.layerDict = None
        self.siteLayer = None
        self.buildingLayer = None
        self.siteRadius = 100 # a default distance
        self.useBoundingBox = False # would use bounding box to get data, faster
        self.sitePropertiesScript = None
        self.force2d = False
        self.getNearbySites = True

    def layerByName(self, name):
        return [n for n in self.layers if n.name == name][0]

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
    # Site objects could be pre-generated in order to make
    # queries faster. There could be a command called
    # 'buildSites' that would create some tables
    # and store some site information.
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
        self.config = ConfigurationInfo()
        self.connection = None
        self.writeMode = 'overwrite' #'overwrite' or 'append' are only options
        self.epsg = 3785 # default epsg, look it up

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
            site_layer = self.config.siteLayer
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
            elif layer == self.config.terrainLayer:
                # process the terrain
                layerSQL = sqls.getLayer(site_layer.name_in_db, layer.name_in_db,
                        layer.cols, id, self.config.siteRadius)
                terrainData = self._run(layerSQL)
                if len(terrainData > 0):
                    # this should create a different json type. How about
                    # 'MESH'?
                    terrainJson = makeTerrainJson(layer, terrainData)

            else: # this is some other layer
                layerSQL = sqls.getLayer(site_layer.name_in_db, layer.name_in_db,
                        layer.cols, id, self.config.siteRadius)
                layerData = self._run(layerSQL)
                if len(layerData) > 0:
                    siteDict["layers"].append(makeLayerJSON(layer, layerData))
        # close connection
        self._close()
        return json.dumps(siteDict)

    def loadDataFile(self, dataFile, verbose=False):
        '''for loading one DataFile object'''
        # make sure some layers exist
        if not self.config.layers:
            self.config.layers = []
        # if a layer with that name exists, get it
        if dataFile.destLayer in [lay.name for lay in self.config.layers]:
            layer = self.config.layerByName(dataFile.destLayer)
        else:
            print 'New Layer:', dataFile.destLayer
            # make a Layer object
            layer = Layer(dataFile.destLayer)
        # we're building the db, so this will be true
        layer.name_in_db = layer.name
        # get configuration info from the DataFile
        if dataFile.isTerrainLayer:
            self.config.terrainLayer = layer
        if dataFile.isBuildingLayer:
            self.config.buildingLayer = layer
        if dataFile.isSiteLayer:
            self.config.siteLayer = layer
        if dataFile.zField:
            layer.zColumn = dataFile.zField
        # put it in the configuration layer list
        self.config.layers.append(layer)
        # now load it
        result = dataFile._load(self)
        # this part should better report progress and stuff
        if verbose:
            print result
        return result

    def loadDataFiles(self, dataFiles, verbose=False):
        '''for loading multiple DataFile objects.'''
        loadedLayers = []
        return_vals = []
        for df in dataFiles:
            if df.destLayer in loadedLayers: # existing layer
                self.writeMode = 'append'
            else: # new layer
                self.writeMode = 'overwrite'
                loadedLayers.append(df.destLayer)
            # load the file, what is returned?
            return_vals.append( self.loadDataFile( df, verbose ))
        return return_vals


def loadFromXlsConfigurationFile( xlsFile, dbinfo, destinationEPSG=3785,
                                  verbose=False):
    projections, files = loader.parseXlsFile( xlsFile )
    ds = DataSource( dbinfo )
    ds.epsg = destinationEPSG
    results = ds.loadDataFiles( files, verbose )
    return ds, results



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
