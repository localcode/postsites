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
from pprint import pprint, pformat

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
        "3D Point":'POINT25D',
        "3D Multi Point":'MULTIPOINT25D',
        "3D Polygon":'MULTIPOLYGON25D',
        "3D Line String":'MULTILINESTRING25D'
        }

xlsInfo = {'proj_cols':[
                "index",
                "epsg code",
                "wkt",],
           'file_cols':[
                'default name',
                'layer name',
                "projection",
                "file path",
                "shape type",
                "is site layer",
                "is terrain",
                "is building layer",
                "z field",]
        }

def cvars(obj):
    v = vars(obj)
    d = {}
    for k in v:
        if k[0] != '_':
            d[k] = v[k]
    return d

def runArgs(args):
    '''run cmd, return (stdout, stderr).'''
    print args
    p = Popen(args, stdout=PIPE, stderr=PIPE, shell=True)
    return p.communicate() # returns (stdout, stderr)

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
    def __init__(self, filePath): # must be tied to a real file
        self.fp = os.path.abspath(filePath) # make sure the path is a good one
        self.filePath = self.fp # shortcut !
        # ._readInfo fails silently, needs error raising.
        self.baseWkt = None
        self.proj = None
        self._readInfo() # this sets many attributes
        self.hasProj = bool(self.baseWkt or self.proj)

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
        else:
            pass

    # this method should be read upon initialization
    def _readInfo(self):
        '''called by __init__, reads info from file to populate attribute values.
        sets defaultName, shpType, and calls _getProj to try to get projection.
        this method depnds on having ogrinfo available on the system PATH. This
        needs lots of error catching because it depends on good input and
        having lots of tools available.'''
        args = ['ogrinfo', '-ro', ('"%s"' % self.filePath)]
        out, err = runArgs( ' '.join(args) )
        if len(err) > 0: # if there's an error
            return err # return the error
        else:
            try:
                rlayName, rshpType = out.split('\n')[2].split(' (') # read ogrinfo results
            except:
                return 'Error running command: %s' % args
            self.defaultName = rlayName.split()[1]
            self.destLayer = self.defaultName
            self.shpType = rshpType.split(')')[0]
            self._readProj()

    # this method should be called to load the file
    # and only after the loading has been configured
    def _getLoadArgs(self, dataSource):
        u, db, pw = dataSource.dbinfo['user'], dataSource.dbinfo['dbname'], dataSource.dbinfo['password']
        args = ['ogr2ogr',
                '-t_srs "EPSG:%s"' % dataSource.epsg,
                '-s_srs "EPSG:%s"' % self.proj.epsg,
                '-f "PostgreSQL"',
                '-%s' % dataSource.writeMode, #'-append', or '-overwrite'
                'PG:"user=%s dbname=%s password=%s"' % (u, db, pw),
                '"%s"' % self.filePath,
                # dbf files falsely claim precisions, the next arg deals with that
                '-lco PRECISION=NO',
                '-nln %s' % self.destLayer,
                '-nlt %s' % shpTypeDict[self.shpType], # get the OGC shape type
                ]
        if dataSource.skipfailures:
            args.insert(1, '-skipfailures')
        if self.zField:
            args.append('-zfield %s' % self.zField )
        return args

    def _load(self, dataSource):
        # depends on subprocess module
        args = self._getLoadArgs( dataSource ) # this needs to be a list, not a string
        # use subprocess to run cmd
        out, err = runArgs(' '.join(args)) # I thought Popen could join these better, but it doesn't :(
        if len(err) > 0: # if there's an error
            return False, err # return the error
        else:
            return True, out

    def _getProjArgs(self, to_epsg, from_epsg, destFilePath, ogrDataFormat):
        args = ['ogr2ogr',
                '-t_srs "EPSG:%s"' % to_epsg,
                '-s_srs "EPSG:%s"' % from_epsg,
                '-f "%s"' % ogrDataFormat,
                '"%s"' % destFilePath,
                '"%s"' % self.filePath,
                ]
        return args

    def project(self, to_epsg, from_epsg=None, destFilePath=None, ogrDataFormat='ESRI Shapefile'):
        '''Projects the DataFile to a new coordinate system, using an EPSG
            code. Destination file path and format are optional.

            This method does not depend on PostgreSQL or the psycopg2 module.
        '''
        if not from_epsg:
            if self.proj:
                from_epsg = self.proj.epsg
            else:
                print 'undeclared projection for this shapefile!'
                raise
        if not destFilePath:
            path, ext = os.path.splitext(self.fp)
            destFilePath = ''.join([path, '_%s' % to_epsg, ext])
        args = self._getProjArgs(to_epsg, from_epsg, destFilePath, ogrDataFormat)
        # use subprocess to run cmd
        out, err = runArgs(' '.join(args)) # I thought Popen could join these better, but it doesn't :(
        if len(err) > 0: # if there's an error
            return False, err # return the error
        else:
            return True, out


class DataDirectory(object):
    '''A DataDirectory object contains information about a folder
    of GIS data, and has methods for loading that data, as well as
    methods for configuring how that data will be loaded.'''
    def __init__(self, folderOrFileList ):
        # read folder or file list
        self._browseFiles( folderOrFileList )
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

    def _browseFiles(self, folderOrFileList ):
        '''called when DataDirectories are created, this method searches the
        designated folder for GIS data files and gathers their information.'''
        # determine whether the incoming data is a list or string
        if type(folderOrFileList) == list:
            # it's a list
            shpFiles = folderOrFileList # done
            self.folder = os.path.split(os.path.commonprefix(shpfiles))[0] # I LOVE stdlib!!!
        elif type(folderOrFileList) == str:
            # it's a folder
            self.folder = folderOrFileList
            shpFiles = getShpFiles(folderOrFileList)
        else:
            print 'please use a valid folder name or list of file paths to make a DataDirectory object'
            return
        # depends on having the PATH set up correctly
        self.uniqueProjections = []
        self.files = []
        self.unprojectedFiles = []
        # set fileList
        for fp in shpFiles:
            df = DataFile( fp) # This line needs ogrinfo to be in the PATH
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
        projs = self.uniqueProjections
        projRows = [[i+1,
                     projs[i].epsg,
                     projs[i].wkt] for i in range(len(projs))]
        projRows.insert(0, xlsInfo['proj_cols']) # column headers in xlsInfo dict
        for r in range(len(projRows)):
            for c in range(len(projRows[r])):
                proj_sheet.write(r, c, projRows[r][c])
        # make a worksheet for the files
        shp_sheet = wb.add_sheet('Shapefiles')
        fileRows = []
        for f in self.files:
            row = []
            row.append(f.defaultName.decode('utf-8'))
            row.append(f.defaultName.decode('utf-8')) # use the default name as the layer name
            if f.proj in self.uniqueProjections:
                row.append(self.uniqueProjections.index(f.proj)+1)
            else:
                row.append('Unknown Projection')
            row.append(f.filePath.decode('utf-8'))
            row.append(f.shpType)
            row.append(f.isSiteLayer)
            row.append(f.isTerrainLayer)
            row.append(f.isBuildingLayer)
            row.append(f.zField)
            fileRows.append(row)
        fileRows.insert(0, xlsInfo['file_cols']) # column headers in xlsInfo dict
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
                rdeturn
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

    def pprintData(self, file_path=None):
        things = []
        folder = 'folder = %s' % self.folder
        projs = 'unique_projections = %s' % pformat([cvars(p) for p in self.uniqueProjections],
                indent=4)
        fs = 'files = %s' % pformat([cvars(f) for f in self.files], indent=4)
        things.append(folder)
        things.append(projs)
        things.append(fs)
        if self.unprojectedFiles:
            ufiles = 'unprojected_files = %s' % pformat([cvars(f) for f in self.unprojectedFiles],
                    indent=4)
            things.append(ufiles)
        s = '\n'.join(things)
        if file_path:
            fobj = open(file_path, 'w')
            fobj.write(s)
            fobj.close()
        else:
            print s

def parseXlsFile(xls_file):
    '''Parses an xls file into Projection and DataFile objects.
    Returns list of Projection objects, and list of DataFile objects.'''
    if not HAS_XLRD:
        print '''
        The xlrd module is not installed or is not available on
        sys.path. This function requires the xlrd module. Please
        install, or add xlrd to sys.path to continue.'''
        return
    book = xlrd.open_workbook(xls_file)
    proj_sheet = book.sheet_by_name('Unique Projections')
    file_sheet = book.sheet_by_name('Shapefiles')
    # Get the column names
    proj_col_names = proj_sheet.row_values(0)
    file_col_names = file_sheet.row_values(0)
    # read the xls file and separate it by column
    # map the columsn to the column names
    pcindex = {}
    fcindex = {}
    for col in xlsInfo['proj_cols']:
        col_index = proj_col_names.index(col)
        pcindex[col] = col_index
    for col in xlsInfo['file_cols']:
        col_index = file_col_names.index(col)
        fcindex[col] = col_index
    # get the rows of each spreadsheet, and snip off the column names
    # that are in the first row
    filePaths = file_sheet.col_values(fcindex['file path'])[1:]
    epsgs = proj_sheet.col_values(pcindex['epsg code'])[1:]
    frows = [file_sheet.row_values(i+1) for i in range(len(filePaths))]
    prows = [proj_sheet.row_values(i+1) for i in range(len(epsgs))]
    # make the projections
    projections = []
    for row in prows:
        proj = Projection(row[pcindex['wkt']])
        proj.epsg = int(row[pcindex['epsg code']])
        projections.append(proj)
    # make the DataFiles
    files = []
    for row in frows:
        f = DataFile(row[fcindex['file path']]) # this will cause it to read the file
        f.destLayer = row[fcindex['layer name']]
        f.isTerrainLayer = bool(row[fcindex['is terrain']])
        f.isSiteLayer = bool(row[fcindex['is site layer']])
        f.isBuildingLayer = bool(row[fcindex['is building layer']])
        f.zField = row[fcindex['z field']]
        f.proj = projections[int(row[fcindex['projection']]) - 1]
        f.hasProj = True
        files.append(f)
    return projections, files

