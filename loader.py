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
from subprocess import Popen, PIPE

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

def runArgs(args):
    '''run cmd, return (stdout, stderr).'''
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    return p.communicate() # returns (stdout, stderr)

def generateLoadArgs(dbInfo, path, shpType, srs_in, srs_out):
    '''generates command line arguments based on configurations
    and information about a specific file.'''
    (userName, dbName, password) = dbInfo['user'], dbInfo['dbname'], dbInfo['password']
    args = ['ogr2ogr',
            '-t_srs "%s"' % srs_out,
            '-s_srs "%s"' % srs_in,
            '-f "PostgreSQL"', '-overwrite',
            'PG:"user=%s dbname=%s password=%s"' % (userName, dbName, password),
            "%s" % path,
            # dbf files falsely claim precisions, the next arg deals with that
            '-lco PRECISION=NO',
            '-nlt %s' % shpType,
            ]
    return args

def getShpFiles(folder):
    """this function returns a list of all the
    shapefiles contained within the input folder
    including the subfolders of that folder"""
    shpList = []
    dirTree = os.walk(os.path.abspath(folder))
    for dirTuple in dirTree:
        dirPath = dirTuple[0]
        files = dirTuple[2]
        for f in files:
            if f[-4:] == '.shp':
                shpList.append(os.path.join(dirPath, f))
    return shpList

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
    def __init__(self, dataDirectory, filePath): # must be tied to a real file
        self.fp = os.path.abspath(filePath) # make sure the path is a good one
        self.filePath = self.fp # shortcut !
        self.dd = dataDirectory
        # ._readInfo fails silently, needs error raising.
        self._readInfo() # this sets many attributes

        ## these attributes depend on a user's configuration and preferences
        self.destLayer = None
        self.isTerrainLayer = False
        self.isBuildingLayer = False
        self.isSiteLayer = False
        self.zField = None

    # this method should be read upon initialization
    def _readProj(self):
        '''called by _getInfo, tries to read proj file if it exists.'''
        projFilePath = os.path.splitext(self.filePath)[0] + '.prj'
        # if proj file exists:
        if os.path.exists(projFilePath):
            wkt = open(projFilePath, 'r').read()
            self.baseWkt = wkt
            self.hasProj = True
        else:
            self.proj = None
            self.hasProj = False

    # this method should be read upon initialization
    def _readInfo(self):
        '''called by __init__, reads info from file to populate attribute values.
        sets defaultName, shpType, and calls _getProj to try to get projection.
        this method depnds on having ogrinfo available on the system PATH.'''
        args = ['ogrinfo', '-ro', self.filePath]
        out, err = runArgs(args)
        if len(err) > 0: # if there's an error
            return err # return the error
        else:
            rlayName, rshpType = out.split('\n')[2].split(' (')
            self.defaultName = rlayName.split()[1]
            self.shpType = rshpType.split(')')[0]
            self._readProj()

    # this method should be called to load the file
    # and only after the loading has been configured
    def _getLoadArgs(self, dataSource):
        return generateLoadArgs(dataSource.dbinfo, # connectioninfo
                              self.filePath, # file path
                              self.shpType, # shape Type
                              'EPSG:%s' % self.proj.epsg, #srs_in
                              'EPSG:%s' % self.dd.destinationEPSG # srs_out
                              )

    def _load(self, dataSource):
        # depends on subprocess module
        args = self._getloadArgs( dataSource ) # this needs to be a list, not a string
        # use subprocess to run cmd
        out, err = runArgs(args)
        if len(err) > 0: # if there's an error
            return False, err # return the error
        else:
            return True, out


class DataDirectory(object):
    '''A DataDirectory object contains information about a folder
    of GIS data, and has methods for loading that data, as well as
    methods for configuring how that data will be loaded.'''
    def __init__(self, folderPath, configFile=None):
        # these should be set upon intialization
        self.folder = folderPath
        self.directory = self.folder # a shortcut!
        self.dir = self.folder # a shortcut!
        self._browseFiles()
        #self.unprojectedFiles = None
        #self.uniqueProjections = self._getUniqueProjs

        # these shouild be configured
        self.targetDataSource = None
        self.destinationEPSG = None

    def configureEPSGs(self, uniqueProjDict):
        '''Used to read a set of unique projections after looking up
        their EPSG codes.'''
        pass

    def _browseFiles(self):
        # depends on having the PATH set up correctly
        import pprint
        self.files = []
        wkts = []
        self.unprojectedFiles = []
        # set fileList
        for fp in getShpFiles(self.folder):
            df = DataFile(self, fp)
            self.files.append( df )
            if df.hasProj: # this file has a proj file
                if df.baseWkt not in wkts:
                    wkts.append(df.baseWkt)
                    projIndex = len(wkts) - 1
                else: #existing proj
                    projIndex = wkts.index(df.baseWkt)
                    # find the proj

            else: # has no proj file
                self.unprojectedFiles.append(df)



        pprint.pprint( self.files )

        # right now I read teh shapefile info in an inefficient way:
            #1. get basic info using ogrinfo
            #2. use the basic info to get more info

        # get the unique projections and unprojected files
        # use ogr or something to get data on each file
        # determine the projection of each file.



