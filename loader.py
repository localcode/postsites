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

# Third Party Imports
try:
    import xlwt
    HAS_XLWT = True
except:
    HAS_XLWT = False

try:
    import xlrd
    HAS_XLRD = True
except:
    HAS_XLRD = False

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

    def _inputFormat(self, index=None):
        return '''
        {
        "index": %s,
        "epsg": %s,
        "wkt": "%s",
        }''' % (str(index), str(self.epsg), self.wkt )

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
        self.configFile = None
        #self.unprojectedFiles = None

        # these shouild be configured
        self.targetDataSource = None
        self.destinationEPSG = None

    def configureEPSGs(self, uniqueProjDict):
        '''Used to read a set of unique projections after looking up
        their EPSG codes.'''
        pass

    def _wkts(self):
        if self.uniqueProjections:
            return [proj.wkt for proj in self.uniqueProjections]
        else:
            return []

    def _browseFiles(self):
        '''called when DataDirectories are created, this method searches the
        designated folder for GIS data files and gathers their information.'''
        # depends on having the PATH set up correctly
        self.uniqueProjections = []
        self.files = []
        self.unprojectedFiles = []
        # set fileList
        for fp in getShpFiles(self.folder):
            df = DataFile(self, fp) # This line needs ogrinfo to be in the PATH
            self.files.append( df ) # add the datafile object
            if df.hasProj: # this file has a proj file
                if df.baseWkt not in self._wkts(): # new proj
                    p = Projection(df.baseWkt) # create Projection object
                    self.uniqueProjections.append(p) # add it to list
                    df.proj = p # tell the file which projection it has
                else: # existing proj
                    p = self.uniqueProjections[self._wkts().index(df.baseWkt)] # lookup wkt
                    df.proj = p # tell the file which projection it has
            else: # has no proj file
                self.unprojectedFiles.append(df)

    def makeXlsConfig(self, filePath=None):
        if not HAS_XLWT:
            print '''
            The xlwt module is not installed or is not available on
            sys.path. This function requires the xlwt module. Please
            install, or add xlwt to sys.path to continue.'''
            return
        if not filePath:
            filePath = 'xls_config_%s.xls' % os.path.split(self.folder)[1].replace(' ','_')
        # make two worksheets
        wb = xlwt.Workbook()
        # make a worksheet for unique projections
        proj_sheet = wb.add_sheet('Unique Projections')
        proj_cols = [
                "index",
                "epsg code",
                "wkt",
                ]
        projs = self.uniqueProjections
        projRows = [[i+1,
                     projs[i].epsg,
                     projs[i].wkt] for i in range(len(projs))]
        projRows.insert(0, proj_cols)
        for r in range(len(projRows)):
            for c in range(len(projRows[r])):
                proj_sheet.write(r, c, projRows[r][c])
        # make a worksheet for the files
        shp_sheet = wb.add_sheet('Shapefiles')
        file_cols = [
                'default name',
                'layer name',
                "projection",
                "file path",
                "shape type",
                "is site layer",
                "is terrain",
                "is building layer",
                "z field",
                ]
        fileRows = []
        for f in self.files:
            row = []
            row.append(f.defaultName)
            row.append(f.defaultName) # use the default name as the layer name
            if f.proj in self.uniqueProjections:
                row.append(self.uniqueProjections.index(f.proj)+1)
            else:
                row.append('Unknown Projection')
            row.append(f.filePath)
            row.append(f.shpType)
            row.append(f.isSiteLayer)
            row.append(f.isTerrainLayer)
            row.append(f.isBuildingLayer)
            row.append(f.zField)
            fileRows.append(row)
        fileRows.insert(0, file_cols)
        for r in range(len(fileRows)):
            for c in range(len(fileRows[r])):
                shp_sheet.write(r, c, fileRows[r][c])
        # save the workbook
        wb.save(filePath)
        self.configFile = filePath
        return filePath

    def printProjections(self):
        projs = self.uniqueProjections
        ps=',\n'.join([projs[i]._inputFormat(i) for i in range(len(projs))])
        s = 'unique_projections = [\n'+ps+'\n]'
        m = '''
"""
Unique Projection output for Data Directory at:
    '%s'

EPSG codes for input can be found using these websites:
    http://www.spatialreference.org
    http://prj2epsg.org/search

"""
''' % self.folder
        print m + s

    def loadProjections(self, proj_list=None, file_path=None):
        if not (file_path or proj_list):
            print 'please enter an input!'
            return
        if file_path: # try to use the file path
            fp = os.path.abspath(file_path)
            if os.path.exists(fp):
                try:
                    # this should get 'unique_projections'
                    eval(open(fp, 'r').read()) # this is probably sketchy to do
                    # but I don't know how to import from a file in the right way
                    # doesn't import actually evaluate the file though?
                    try:
                        proj_list = unique_projections
                    except:
                        print 'a python list called "unique_projections" does not exist in the file %s' % file_path
                        print 'Please rename the list, or edit the file and try again.'
                        return
                except:
                    print 'File at %s\ncould not be read correctly.' % file_path
                    print 'please edit the file path or ensure that the file does not contain errors.'
                    return
            else:
                print 'no file exists at %s' % fp
                return
        # next, look at proj_list
        if proj_list and type(proj_list) == list: # try to use the projection list
            try:
                for i in range(len(proj_list)):
                    proj = proj_list[i]
                    p = self.uniqueProjections[proj['index']]
                    p.epsg = proj['epsg']
                    p.wkt = proj['wkt']
            except:
                print 'Projections could not be loaded from projection list.'
                print 'Ensure that they are the correct dictionary format,'
                print 'and contain "wkt", "epsg", and "index" codes.'
                return
        else:
            print "Something's wrong with the input"
            print "It might not be a valid python list object"
            print "It appears to be a %s" % type(proj_list)
            return



