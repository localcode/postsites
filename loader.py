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

if PATH_TO_OGR:
    sys.path.append(PATH_TO_OGR)
else:
    pass

class Projection(object):
    def __init__(self, wkt=None):
        if wkt:
            self.wkt = wkt
        else:
            self.wkt = None
        self.epsg = None

    def setEPSG(self, epsgCode):
        self.epsg = epsgCode

class DataFile(object):
    def __init__(self, filePath):
        self.fp = os.path.abspath(filePath)
        self.filePath = sel.fp
        self.hasProj = False
        self.proj = None
        self.destLayer = None
        self.isTerrainLayer = False
        self.isBuildingLayer = False
        self.isSiteLayer = False

        self.getProjection()

    def getProjection(self):


        self.hasProj = None
        self.proj = Projection(wkt)

    def getInfo(self):
        self.filePath


class DataDirectory(object):
    def __init__(self, folderPath, configFile=None):
        self.folder = folderPath
        self.directory = folderPath
        self.dir = folderPath
        self.projections = self._getUniqueProjs
        self.targetDataSource = None

    def uniqueProjections(self):
        # This should generate a set of Projection objects that can be read to
        # determine the correct destination projections for each one.
        pass

