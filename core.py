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
from json_utils import handler # necessary for handling datetimes

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
    points = []
    pointAttributes = [] # a list of attribute values for each point
    for row in terrainData: # each row will contain a point
        rawJSON, columnData = row[0], row[1:]
        geomJSON = json.loads(rawJSON)
        # here is where I should triangulate it.
        point = geomJSON['coordinates']
        if len(point) == 3:
            pointZ = point[2]
        elif layer.zColumn:
            pointZ = columnData[layer.cols.index(layer.zColumn)]
        else:
            pointZ = 0.0
        pointX, pointY = point[0], point[1]
        points2d.append((pointX, pointY))
        points.append((pointX, pointY, pointZ))
        # this creates one list for each point
        pointAttributes.append(columnData)
    # now triangulate the points2d
    tris = []
    for array in triangulate(points2d):
        face = [int(n) for n in array]
        tris.append(face)
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

    def setSiteLayer(self, name):
        self.siteLayer = self.layerByName(name)
        return self

    def setTerrainLayer(self, name):
        self.terrainLayer = self.layerByName(name)
        return self

    def setBuildingLayer(self, name):
        self.buildingLayer = self.layerByName(name)
        return self

class Layer(object):
    """Used to hold information about individual layers."""

    def __init__(self, name):
        self.name = name
        self.name_in_db = name
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
        self.skipfailures = False
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

    def _runMultiple(self, sqls):
        datas = []
        self._connect()
        for sql in sqls:
            datas.append(self._run(sql))
        self._close()
        return datas

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
            outList = self.config.layers # this assumes the layers have been setup
        else:
            self._connect() # but if they haven't been setup, then go get them
            regexMask = '^pg_|^sql_|spatial_ref_sys|geometry_columns'
            s = "SELECT tablename FROM pg_tables WHERE tablename !~'%s';" % regexMask
            data = self._run(s)# return a list of the tables in the db
            c = "SELECT column_name FROM information_schema.columns WHERE table_name = '%s' AND column_name !~'wkb_geometry';"
            for row in data: # data is a list of tuples
                layer = Layer(row[0])
                # now get the column names
                coldata = self._run(c % layer.name)
                layer.cols = [col[0] for col in coldata]
                outList.append(layer) #only one item in each tuple
            self._close()
        dictTemplate = "'%s':{ 'name': '%s', 'cols':[%s]}"
        formattedLayerDicts = [( dictTemplate % (layer.name_in_db, layer.name,
            ', '.join([("'%s'" % r) for r in layer.cols]))) for layer in outList]
        prefix = 'all_database_layers = {\n'
        suffix = '\n}'
        formatted = prefix + ',\n'.join(formattedLayerDicts) + suffix
        if filePath != None:
            f = open(filePath, 'w')
            f.write(formatted)
            f.close()
            return outList
        else:
            return formatted

    def loadLayerDict(self, fileOrDict):
        if type(fileOrDict) != dict: #its a file name
            raw = open(fileOrDict, 'r').read()
            layDict = eval(raw)
        else: # its a dictionary
            layDict = fileOrDict
        layers = dictToLayers(layDict)
        self.config.layers = layers
        self.config.layerDict = layDict
        return self.config #return the ConfigurationInfo object

    def getSiteJson(self, id=None):
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
                if len(terrainData) > 0:
                    # this should create a different json type. How about
                    # 'MESH'?
                    terrainJson = makeTerrainJSON(layer, terrainData)
                    siteDict["layers"].append(terrainJson)

            else: # this is some other layer
                layerSQL = sqls.getLayer(site_layer.name_in_db, layer.name_in_db,
                        layer.cols, id, self.config.siteRadius)
                layerData = self._run(layerSQL)
                if len(layerData) > 0:
                    siteDict["layers"].append(makeLayerJSON(layer, layerData))
        # close connection
        self._close()
        return json.dumps(siteDict, default=handler)

    def loadDataFile(self, dataFile, verbose=False, skipfailures=False):
        '''for loading one DataFile object'''
        if 'PGCLIENTENCODING' not in os.environ:
            os.environ['PGCLIENTENCODING'] = 'LATIN1'
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
        # set skipfailures
        if skipfailures:
            self.skipfailures = True
        # now load it
        result = dataFile._load(self)
        # this part should better report progress and stuff
        if verbose:
            print result
        return result

    def loadDataFiles(self, dataFiles, verbose=False, skipfailures=False):
        '''for loading multiple DataFile objects.'''
        if 'PGCLIENTENCODING' not in os.environ:
            os.environ['PGCLIENTENCODING'] = 'LATIN1'
        loadedLayers = []
        return_vals = []
        for df in dataFiles:
            if df.destLayer in loadedLayers: # existing layer
                self.writeMode = 'append'
            else: # new layer
                self.writeMode = 'overwrite'
                loadedLayers.append(df.destLayer)
            # load the file, what is returned?
            return_vals.append( self.loadDataFile( df, verbose, skipfailures ))
        return return_vals


def makeXlsConfigurationFile( folder, filePath=None ):

    dd = loader.DataDirectory( folder ) # this should make a DatSource object and
    #read everything.
    return dd.makeXlsConfig( filePath )

def loadFromXlsConfigurationFile( xlsFile, dbinfo, destinationEPSG=3785,
                                  verbose=False, skipfailures=False):
    projections, files = loader.parseXlsFile( xlsFile )
    ds = DataSource( dbinfo )
    ds.epsg = destinationEPSG
    results = ds.loadDataFiles( files, verbose, skipfailures )
    return ds, results

