
# Creates a new layer in a PostGIS database
# with an ogc_fid attribute
# Variables:
# %(layer_name)s
def createTable(tableName):
    return """CREATE TABLE %(layer_name)s (
  ogc_fid serial NOT NULL
);
""" % {'layer_name':tableName}

# Takes the points from one table and dumps
# them into another table. Might need
# point_layer to be made first.
# Variables:
# %(point_layer)s the layer to dump points into
# %(from_layer)s the layer to dum points from
def dumpPoints(fromLayer, toLayer):
    return """INSERT INTO
    %(point_layer)s (wkb_geometry)
    SELECT
        (g.gdump).geom
    FROM (
        SELECT
            ST_DumpPoints(%(from_layer)s.wkb_geometry) AS gdump
        FROM
            %(from_layer)s
        ) AS g;
""" % {'from_layer':fromLayer, 'point_layer':toLayer}


# Gets all the other objects from a layer
# that are within the site_radius distance from
# the site in question
# Variables:
# %(site_layer)s the layer used for sites
# %(layer)s the layer to retrieve data from
# %(columns)s the columns to return attribute data from
# %(site_id)s the id of the site in question
# %(site_radius)s the distance from the site to search
def getLayer(siteLayer, layer, cols, id, siteRadius):
    return """SELECT
	ST_AsGeoJSON(ST_Translate(%(layer)s.wkb_geometry,
    -ST_X(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s))),
    -ST_Y(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s)))
    )) %(columns)s
    FROM
        %(layer)s
    WHERE
        ST_DWithin(%(layer)s.wkb_geometry,
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s)
        , %(site_radius)s)
""" % {'site_layer':siteLayer, 'layer':layer, 'columns':cols, 'site_id':id, 'site_radius':siteRadius}


# Selects the site in question
# Variables:
# %(site_layer)s the layer used for sites
# %(columns)s the columns to return attribute data from
# %(site_id)s the id of the site in question
# %(site_radius)s the distance from the site to search
def getSite(siteLayer, cols, id, siteRadius):
    return """SELECT
	ST_AsGeoJSON(ST_Translate(%(site_layer)s.wkb_geometry,
    -ST_X(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s))),
    -ST_Y(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s)))
    )) %(columns)s
FROM
    %(site_layer)s
WHERE
    %(site_layer)s.ogc_fid = %(site_id)s
""" % {'site_layer':siteLayer, 'columns':cols, 'site_id':id, 'site_radius':siteRadius}


# Finds the closest z value in the terrain layer
# to some geometry and returns that z value.
# uses radius to search within.
# Variables:
# %(from_layer)s the layer to get a z value for
# %(terrain_layer)s the layer to get a z value from
# %(max_distance)s the maximum distance to search within for a z value (smaller=faster)
# %(id)s the object id (in from_layer) to get a z value for
def nearestZ(forLayer, terrainLayer, searchDistance, id):
    return """SELECT ST_Z(t.wkb_geometry)
FROM %(terrain_layer)s As t, %(from_layer)s As f
WHERE ST_DWithin( t.wkb_geometry, (ST_Centroid(f.wkb_geometry)) , %(max_distance)s)
AND f.ogc_fid = %(id)s
ORDER BY ST_Distance(t.wkb_geometry, (ST_Centroid(f.wkb_geometry)))
LIMIT 1;
""" % {'from_layer':forLayer, 'terrain_layer':terrainLayer, 'max_distance':searchDistance, 'id':id}


# Gets all the other objects from the site layer
# that are within the site_radius distance from
# the site in question
# Variables:
# %(site_layer)s the layer used for sites
# %(columns)s the columns to return attribute data from
# %(site_id)s the id of the site in question
# %(site_radius)s the distance from the site to search
def otherSites(siteLayer, cols, id, siteRadius):
    return """SELECT
	ST_AsGeoJSON(ST_Translate(%(site_layer)s.wkb_geometry,
    -ST_X(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s))),
    -ST_Y(ST_Centroid(
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s)))
    )) %(columns)s
    FROM
        %(site_layer)s
    WHERE
        ST_DWithin(%(site_layer)s.wkb_geometry,
        (SELECT
            %(site_layer)s.wkb_geometry
        FROM
            %(site_layer)s
        WHERE
            %(site_layer)s.ogc_fid = %(site_id)s)
        , %(site_radius)s)
    AND
        %(site_layer)s.ogc_fid != %(site_id)s
""" % {'site_layer':siteLayer, 'columns':cols, 'site_id':id, 'site_radius':siteRadius}


