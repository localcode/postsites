"""
The following example shows how to import a site
model to Maya for one site, including attributes:
>>> baseModel(65)
"""

import db
import sql
from sql import sqlRootPath
import layers
import shapely
import shapely.wkt 
import pymel.core as pm
import triforce

def zPt(coordTuple):
    """This function ensures that each set of coordinates
    for any given point has 3 values (x,y,z) not just (x,y).
    """
    c = coordTuple
    x = c[0]
    y = c[1]
    if len(c) == 3:
        z = c[2]
    else:
        z = 0.0
    point = (x,y,z)
    return (x,y,z)

def ptListToPolyline(ptList):
    """ This uses a list of points to create a
    polyline curve in Maya, and then returns
    the name of the created curve.
    """
    pts = []
    for pt in ptList:
        newPt = zPt(pt)
        pts.append(newPt)
    cv = pm.curve(p=pts, degree=1.0)
    return cv

def makePolygonsWithAttr(listOfGeomAttDictTuples):
    """This function takes a list of tuples, each
    tuple containing first a point list, and second
    a dictionary of attributes where the keys are the
    names of the attributes and the values are the 
    corresponding values for each attribute, then the
    function creates a polygon from each point list and
    for that polygon, creates an attribute for each
    attribute in the attribute dictionary. The return value
    is a list of the names of all the created polygons."""
    # create an empty list to hold results
    curves = []
    for item in listOfGeomAttDictTuples:
        # each item consists of a point list, and
        # an attribute dictionary
        pointList, attDict = item[0], item[1]
        # this should return the name of the item
        curve = ptListToPolyline(pointList)
        for key in attDict:
            # ln and sn, are long name and short name respectively
            pm.addAttr(curve, ln=key, sn=key, dt="string")
            # attKey creates a handle that whould point direclty to
            # the attribute on that specific object
            attKey = '%s.%s' % (curve, key)
            # and here we set the attribute to the corresponding
            # value.
            pm.setAttr(attKey, attDict[key], typ="string")
        # finally add the name of the object to the list
        # of results.
        curves.append(curve)
    return curves

def makePolygons(listOfPointLists):
    """ This takes a set of point lists
    and creates a polyline for each point
    list, returning the names of the new
    polylines."""
    curves = []
    for pointList in listOfPointLists:
        curves.append(ptListToPolyline(pointList))
    return curves

def polygonQuery(connection, sql):
    """This takes an SQL query, runs it,
    and creates polygons out of it. This function
    is still being fleshed out, and needs to filter
    out the necessary information for dealing with
    MultiPolygons, and the interior and exterior rings
    of Polygons."""
    data = db.runopen(connection, sql)
    geom = []
    for rowTuple in data:
        ewkt = rowTuple[0]
        cleaned_ewkt = db.removeSRID(ewkt)
        multiPolygon = shapely.wkt.loads(cleaned_ewkt)
        try:
            for polygon in multiPolygon:
                geom.append(polygon.exterior.coords)
        except:
            return 'error reading polygons in multipolygons'
    return geom

def queryToPolygons(connection, sql):
    """This function combines the makePolygons function
    with the polygonQuery function in order to move from
    an sql statemetn to maya polygons in one step."""
    return makePolygons(polygonQuery(connection, sql))

def queryToPolygonsWithAttr(connection, sql, attrNames):
    """This function takes an open database connection
    (a psycopg2 object, refer to psycopg2 docs and the db
    module for more info), an sql statement, and a list of
    attribute names, and uses these three things to construct
    a set of polygons with attributes in Maya. the return value
    is a list of the names of the created polygons."""
    data = db.runopen(connection, sql)
    items = []
    for rowTuple in data:
        ewkt = rowTuple[0]
        attData = rowTuple[1:]
        attDict = dict(zip(attrNames, attData))
        cleaned_ewkt = db.removeSRID(ewkt)
        multiPolygon = shapely.wkt.loads(cleaned_ewkt)
        try:
            for polygon in multiPolygon:
                itemTuple = (polygon.exterior.coords, attDict)
                items.append(itemTuple)
        except:
            return 'error reading polygons in multipolygons'
    return makePolygonsWithAttr(items)

def makeMesh(pointList, triangulationIndices):
    """This function receives a list of points, and a list of index triplets
    indicating the three points to use from the list to create triangular faces.
    It then creates a mesh in Maya using these points and indices, and returns
    the name of the created mesh."""
    polys = []
    for i in range(len(triangulationIndices)):
        face = triangulationIndices[i]
        coords = []
        for index in face:
            coords.append(pointList[index])
        polys.append(pm.modeling.polyCreateFacet(p=coords) )
    pm.select(polys)
    mesh = pm.language.mel.eval('CombinePolygons;')
    return mesh

def queryToMesh(connection, sql):
    """This function takes an open database connection
    (a psycopg2 object, refer to psycopg2 docs and the db
    module for more info), an sql statement
    and uses these things to construct
    a mesh in Maya. The return value is the name of the 
    created mesh."""
    data = db.runopen(connection, sql)
    points = []
    twoDpoints = []
    Zs = []
    for rowTuple in data:
        ewkt = rowTuple[0]
        cleaned_ewkt = db.removeSRID(ewkt)
        p = shapely.wkt.loads(cleaned_ewkt)
        point = (p.x, p.y, p.z)
        xy = (p.x,p.y) 
        points.append(point)
        twoDpoints.append(xy)
        Zs.append(p.z)
    # build a structure from delaunay triangulation
    triStructure = triforce.triangulate(twoDpoints)
    # now I need to turn the points and structure into a mesh
    return makeMesh(points, triStructure)

def moveToLayer(layerName, objectList=[]):
    """This function takes a set of objects and puts them onto
    a designated layer. If the layer does not yet exist, it is created.
    """
    if pm.objExists(layerName) == False: # the layer does not exist
        pm.select(objectList)
        pm.createDisplayLayer(name=layerName)
    else: # the layer already exists
        pm.editDisplayLayerMembers( layerName, objectList )

def baseModel(site_id):
    """Based on an input site ID, this function
    runs an sql query to the PostGIS database and
    collects the geometry for each layer, and then
    places that geometry on a designated layer in
    Maya and stores the attributes of the geometry
    in the maya geometry."""
    s = site_id

    # open a database connection
    conn = db.connect()

    # get the information for the vacant parcels layer
    parcelCols = layers.sites['vacantparcels'][1:]

    # generate the sql for the specific site
    parcelSQL = sql.getParcel( s , parcelCols)
    # create a polygon in Maya for the site itself
    parcel = queryToPolygonsWithAttr(conn, parcelSQL, parcelCols)
    moveToLayer('site', parcel)

    # generate the sql for the nearby sites
    otherParcelsSQL = sql.getOtherParcels(s, parcelCols)
    # create polygons in Maya for the other neaarby vacant parcels
    otherParcels = queryToPolygonsWithAttr(conn, otherParcelsSQL, parcelCols)
    moveToLayer('vacantparcels', otherParcels)

    # combine the sites and physical layer dictionaries into one
    # dictionary
    sitesAndContext = dict(layers.sites, **layers.physical)
    
    noImport = ['vacantparcels']

    for key in sitesAndContext:
        # for every layer besides the vacant parcels
        # (because we already did them)
        if key not in noImport:
            # get the layer name and layer attributes
            layName = sitesAndContext[key][0]
            layAttributes = sitesAndContext[key][1:]
            # generate the sql statement
            layerSQL = sql.oneLayer( s, layName, layAttributes ) + ';'
            if key == 'terrain':
                # make a mesh from the terrain points
                mGeom = queryToMesh(conn, layerSQL)
            else:
                # create the polygons in Maya
                mGeom = queryToPolygonsWithAttr(conn, layerSQL, layAttributes )
            # move the polygons to the corresponding layer in Maya
            moveToLayer(key, mGeom)
    # close the database connection
    conn.close()
    
def deleteEverything():
    """deletes all layers and objects in the maya scene."""
    everything = pm.ls()
    undeleteables = pm.ls(ud=True)
    try:
        pm.delete(everything)    
    except:
        pass

