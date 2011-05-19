"""
This module is used to construct sql statements,
sometimes using templates that are written out
in text files in a local folder.

Usage Example:
>>> import sql, db
>>> layers = sql.physLayers()
>>> print layers
['doitt_building_01_28jul2009', 'doitt_hydrography_01_282009', 'doitt_median_01_28jul2009', 'doitt_hydrography_structure_01_28jul2009', 'doitt_sidewalk_01_28jul2009', 'doitt_transportation_structure_01_28jul2009']
>>> siteID = 59
>>> sqlRequest = sql.getLayers(siteID, layers)
>>> data = db.run(sqlRequest)
>>> len(data)
5
"""

import layers
sqlRootPath = 'C:\\Users\\gallery\\LocalCodeNY\\PythonScripts'

def physLayers():
    layDict = {}
    for key in layers.physical:
        layDict[layers.physical[key][0]] = layers.physical[key][1:]
    return layDict

def amenityLayers():
    layDict = {}
    for key in layers.amenities:
        layDict[layers.amenities[key][0]] = layers.amenities[key][1:]
    return layDict

def siteLayers():
    layDict = {}
    for key in layers.sites:
        layDict[layers.sites[key][0]] = layers.sites[key][1:]
    return layDict

def healthLayers():
    layDict = {}
    for key in layers.health:
        layDict[layers.health[key][0]] = layers.health[key][1:]
    return layDict

def render(filePath, variableDict):
    """
    Returns a string based on reading some template,
    as designated by the file path, and then replacing
    each key in the variableDict with the value in 
    variableDict associated with that key.
    """
    sql = open(filePath, 'r').read()
    for key in variableDict:
        sql = sql.replace(key, variableDict[key])
    return sql

def oneLayer( site_id, layer, columns=[]):
    """returns the sql statement to get the geometry and
    other optional columns (as a list of strings) of 
    information based on which features touch the bounding 
    box of the parcel with the given id.
    Usage Example:
    >>> sId = 72
    >>> layer = 'roads'
    >>> cols = ['length', 'azimuth']
    >>> sqlStatement = oneLayer(sId, layer, cols)
    """
    template = '%s\\one_layer.sql' % sqlRootPath
    colString = ''
    for col in columns:
        colString += ', %s.%s' % (layer, col)
    varD = {
        '$table':layer,
        '$columns':colString,
        '$site_id':str(site_id)
        }
    return render(template, varD)

def getParcel( site_id, columns = []):
    """Returns an SQL statement to retrieve a specific
    parcel from the newyork_parcels layer, along with
    any columns desired."""
    template = '%s\\parcel.sql' % sqlRootPath
    colString = ''
    for col in columns:
        colString += ', %s.%s' % ('newyork_parcels', col)
    varD = {
        '$site_id':str(site_id),
        '$columns':colString,
        }
    return render(template, varD)

def getOtherParcels( site_id, columns = []):
    template = '%s\\otherParcels.sql' % sqlRootPath
    colString = ''
    for col in columns:
        colString += ', %s.%s' % ('newyork_parcels', col)
    varD = {
        '$site_id':str(site_id),
        '$columns':colString,
        }
    return render(template, varD)

def getLayers(site_id, layerList, columnsDict={}):
    """
    returns an sql statement to get the geometry and
    any optional columns for a set of layers, by finding
    which features in each layer overlap the bounding box
    of the parcel with the input site id. Each key in the
    columnsDict should precisely match one of the layer
    names, and the value that corresponds to each key should
    be a list of column name strings.
    Usage Example:
    >>> sId = 34
    >>> layers = ['roads', 'parking_lots', 'trees']
    >>> colsDict = {'roads':['length'], 'parking_lots':['area', 'rate']}
    >>> sqlStatement = getLayers( sId, layers, colsDict )
    """
    union = '\nUNION ALL\n\n'
    parcels = 'newyork_parcels'
    if parcels in columnsDict:
        cols = columnsDict[parcels]
        sqlString = getParcel( site_id, cols )
    else:
        sqlString = getParcel( site_id )
    for layer in layerList:
        sqlString += union
        if layer in columnsDict:
            cols = columnsDict[layer]
            sqlString += oneLayer(site_id, layer, cols)
        else:
            sqlString += oneLayer(site_id, layer)
    sqlString += ';'
    return sqlString
    
        
        
    
        


    
        


