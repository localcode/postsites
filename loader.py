"""
A module for loading data into a PostGIS database for PostSites

Planned Use:

    >>> # select a folder to load data from
    >>> folder = '/Users/benjamin/projects/localcode/gis_data/'
    >>> # use that folder to create a DataDirectory object
    >>> dd = DataDirectory(folder)
    >>> # see all the unique projections in the directory
    >>> dd.uniqueProjections
    >>> # See and edit a dictionary of WKT projections and EPSG codes
    >>> dd.projectionDictionary
    >>> # output a file for adjusting the settings
    >>> dd.configureAll()
    >>> # load the edited file in order to set up the database correctly
    >>> dd.loadConfiguration(config_edited.py)
    >>> from postsites import DataSource
    >>> ds = DataSource({'user':'postgis','dbname':'mydb','password':'postgres'})
    >>> # load all designated files in the directory
    >>> dd.loadAll( ds )
    >>> # load a particular file, and give it a layer name
    >>> dd.loadOne( ds, 'outlines.shp', 'state_outlines')

"""
# Standard Library Imports
import os
import sys

# This module should check for and find the
# necessary GIS libraries for loading data.
#if PATH_TO_OGR:
    #sys.path.append(PATH_TO_OGR)
#else:
    #pass

shpTypeDict = {
        "Polygon":'MULTIPOLYGON',
        "Point":'POINT',
        "Line String":'MULTILINESTRING',
        "3D Multi Point":'MULTIPOINT25D',
        "3D Polygon":'MULTIPOLYGON25D',
        "3D Line String":'MULTILINESTRING25D'
        }

class Projection(object):
    '''A Projection object is used to wrap up a particular spatial reference
    system or spatial projection and is helpful for translating between
    Well-Known Text (WKT) and EPSG codes (which are used by PostGIS).'''
    def __init__(self, wkt=None):
        self.wkt = wkt
        self.epsg = None

    def setEPSG(self, epsgCode):
        self.epsg = epsgCode

    #def fetchRepresentations(self, epsgCode=None):
        #'''connects to the internet and downloads multiple
        #representations of this projection from spatialreference.org.'''
        #if not epsgCode:
            #epsgCode = self.epsg
        #if epsgCode and urlLib():
            #self.projText =
            #self.esriWKT =
            #self.readableWKT =
            #self.ogcWKT =
            #self.postGisInsertSQL =
            #pass
        #else:
            #return 'must set EPSG code before fetching all representations'

class DataFile(object):
    '''A DataFile obect holds information about a particular file of GIS data,
    and can be used to configure the way that the file should be loaded into
    the database.'''
    def __init__(self, filePath): # must be tied to a real file
        self.fp = os.path.abspath(filePath) # make sure the path is a good one
        self.filePath = self.fp # look, two ways to see where the file is
        # these attributes should be set when first initiated:
        self.hasProj = False
        self.proj = None
        self.shpType = None
        self.getProjection()
        # these attributes depend on a user's configuration and preferences
        self.destLayer = None
        self.isTerrainLayer = False
        self.isBuildingLayer = False
        self.isSiteLayer = False

    # this methd should be read upon initialization
    def getProjection(self):
        self.hasProj = None
        self.proj = Projection(wkt)

    # this methd should be read upon initialization
    def getInfo(self):
        self.filePath


class DataDirectory(object):
    '''A DataDirectory object contains information about a folder
    of GIS data, and has methods for loading that data, as well as
    methods for configuring how that data will be loaded.'''
    def __init__(self, folderPath, configFile=None):
        self.folder = folderPath
        self.directory = self.folder # a shortcut!
        self.dir = self.folder # a shortcut!
        self._readFilesForInfo()
        self.uniqueProjections = self._getUniqueProjs
        self.targetDataSource = None
        self.unprojectedFiles = None

    def configureEPSGs(self, uniqueProjDict):
        '''Used to read a set of unique projections after looking up
        their EPSG codes.'''
        pass

    def _readFilesForInfo():
        # depends on having the PATH set up correctly
        # get the unique projections and unprojected files
        # use ogr or something to get data on each file
        # determine the projection of each file.



