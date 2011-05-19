import os
from srid import sridSearch
# from django.contrib.gis.gdal import *

# $ python manage.py ogrinspect [options] <data_source> <model_name> [options]
# $ python manage.py ogrinspect world/data/TM_WORLD_BORDERS-0.3.shp WorldBorders --srid=4326 --mapping --multi

# A few notes about the command-line options given above:

# The --srid=4326 option sets the SRID for the geographic field.
# The --mapping option tells ogrinspect to also generate a mapping dictionary for use with LayerMapping.
# The --multi option is specified so that the geographic field is a MultiPolygonField instead of just a PolygonField.

# get the list of shapefiles

# CONSTANTS

shpTypeDict = {
        "Polygon":'MULTIPOLYGON',
        "Point":'POINT',
        "Line String":'LINESTRING',
        "3D Polygon":'MULTIPOLYGON25D'
        }

projSRIDList = (
                'EPSG:4269',
                'ESRI:102718',
                'ESRI:102718',
                'EPSG:26918') 

def shpToPostgreSQL(path, shpType, srs_in, srs_out):
    """This function uses ogr2ogr to load ESRI shapefiles
    into a PostgreSQL database. ogr2ogr must be installed.
    For now, after 'PG:' the 'host=' variable is not listed
    and therefore the command will default to localhost."""
    # dbf files may claim precisions for fields that do not obey them
    # which may result in field overflow errors during ogr2ogr conversion
    # the precis allows ogr2ogr to ignore the dbf precisions
    # and to simply assign appropriate precisions
    precis = '-lco PRECISION=NO'
    (userName, dbName, password) = ('postgres', 'spatial_databank', 'secret_passwordz')
    # in this operation, existing versions are overwritten
    cmd = 'ogr2ogr -a_srs "%s" -t_srs "%s" -f "PostgreSQL" -overwrite PG:"user=%s dbname=%s password=%s" %s %s -nlt %s' % (srs_in, srs_out, userName, dbName, password, path, precis, shpType)
    return cmd

def getShpType(fullShpInfo):
    s = 'Geometry: '
    strtIndx = fullShpInfo.find(s) + len(s)
    endIndx = fullShpInfo.find('\n', strtIndx)
    return shpTypeDict[fullShpInfo[strtIndx:endIndx]]

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

def out(someList, fileName="result.txt"):
    """dumps some results into a text file"""
    f = open(fileName, "w")
    for i in someList:
        f.write(str(i)+'\n')
    f.close
    os.startfile(fileName)
    
def getShpName(path):
    ogrBaseInfo = getBaseShpInfo(path)
    pos = ogrBaseInfo.find('1: ')
    info = ogrBaseInfo[(pos+3):].split()[0]
    return info

def getBaseShpInfo(path):
    """getBaseShpInfo runs ogrinfo on a shp file to get the name of the contained dataset."""
    ini = 'ogrinfo'
    full = '-so'
    baseInfo = os.popen(ini+' '+path).read()
    return baseInfo

def getShpInfo(path):
    """getShpInfo runs getBaseShpInfo and getShpName to retrieve the name of the contained dataset
    and then reruns ogrinfo to output a detailed set of information on a shp file."""
    ini = 'ogrinfo'
    full = '-so'
    fullInfo = os.popen(ini+' '+full+' '+path+' '+getShpName(path)).read()
    return fullInfo

def filterProj(rawProj):
    rev = rawProj[::-1]
    if rev[:2] != ']]':
        newEnd = rev.find(']]')
        newProj = rev[newEnd:][::-1]
    else:
        newProj = rawProj
    return newProj

def getProj(fullShpInfo):
    """Retrieves the projection information from the full detailed ogrinfo print out."""
    startPos = fullShpInfo.find('PROJCS')
    if startPos == -1:
        startPos = fullShpInfo.find('GEOGCS')
        if startPos == -1:
            return "ERROR: No projection information found."
    unitPos = fullShpInfo.find('UNIT')
    unitPos2 = fullShpInfo.find('UNIT', unitPos+len('UNIT'))
    if unitPos2 > unitPos:
        unitPos = unitPos2
    endPos = fullShpInfo.find('\n',unitPos)
    projInfo = filterProj(fullShpInfo[startPos:(endPos+3)])
    return projInfo

def getSRID(fullShpInfo):
    """This function depends on geodjango"""
    raw_wkt = getProj(fullShpInfo)
    m = raw_wkt.split()
    x = ''
    wkt = x.join(m)
    print wkt
    ref = SpatialReference.from_esri(wkt)
    print ref
    return ref.srid

def createModel(path, fileName="ogrmodel.py", srid=None):
    prefix = "python manage.py ogrinspect "
    dsInfo = path +' '+ getShpName(path) 
    suffix = " --mapping"
    if srid != None:
        suffix = " --srid="+str(srid)+suffix
    cmd = prefix + dsInfo + suffix
    print cmd
    os.system(cmd)

def getUniqueProjections(folder):
    """This function searches the directory tree of a folder
    and returns a tuple containing two lists. The first list
    contains every unique projection found among all the .shp
    files in the tree of folders. The second list contains
    the complete file path of any .shp files whose projection
    information was unreadable or nonexistent."""
    shpList = getShpFiles(folder)
    projList = []
    err = "ERROR: No projection information found."
    errList = []
    for i in shpList:
        info = getShpInfo(i)
        proj = getProj(info)
        if proj == err:
            errList.append(i)
        if proj not in projList and proj != err:
            projList.append(proj)
    outTuple = (projList, errList)
    return outTuple

def getUniqueShpTypes(folder):
    typeList = []
    for i in getShpFiles(folder):
        info = getShpInfo(i)
        shpType = getShpType(info)
        if shpType not in typeList:
            typeList.append(shpType)
    return typeList

def projSRIDmap(projList, fileName='proj-srid-map.txt'):
    """This function creates a text file for making a map between
    the unique projections read from a set of shapefiles to 
    specific SRID codes in the spatial_ref_sys table of a 
    spatial_databank enabled database. The textfile can later be loaded
    in order to map each shapefile to it's correct projection information."""
    f = open(fileName, 'w')
    for i in range(len(projList)):
        proj = projList[i]
        f.write("--START PROJECTION INFO "+str(i)+'--\n')
        f.write(proj+'\n')
        f.write("POSTGRES UNIQUE SRID: "+'\n')
        f.write("--END PROJECTION INFO "+str(i)+"--\n")
    f.close()

def testProjMap(folder):
    s = 'proj'
    e = '.txt'
    projList = getUniqueProjections(folder)[0]
    shpList = getShpFiles(folder)
    for j in shpList:
        proj = getProj(getShpInfo(j))
        if proj in projList:
            idx = projList.index(proj)
            print idx, '-', projSRIDDict[idx]

def loadOneShpFile(path):
    info = getShpInfo(path)
    shpType = getShpType(info)
    srs_in = projSRIDList[1]
    srs_out = 'EPSG:3725' # UTM zone 18N NAD 1983 http://spatialreference.org/ref/epsg/3725/
    return shpToPostgreSQL(path, shpType, srs_in, srs_out)

def loadMany(folder, srsOut):
    out = getUniqueProjections(folder)
    badList = out[1]
    projList = out[0]
    cmdList = []
    for i in getShpFiles(folder):
        if i not in badList:
            info = getShpInfo(i)
            srs = projSRIDList[projList.index(getProj(info))]
            shpType = getShpType(info)
            cmdList.append(shpToPostgreSQL(i, shpType, srs, srsOut))
    return cmdList

if __name__=="__main__":
    
    folder = 'C:\\Users\\gallery\\Desktop\\Local_Code_NY'
    shp = "C:\\Users\\gallery\\Desktop\\Local_Code_NY\\New_York\\Transportation_Infrastructure\\DOITT_TRANSPORTATION_STRUCTURE_01_28JUL2009.shp"
    srsOut = 'EPSG:3725' 
    os.system(loadOneShpFile(shp))
    # for j in loadMany(folder, srsOut):
    #     os.system(j)
    
