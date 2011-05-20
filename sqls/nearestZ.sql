--Finds the closest z value in the terrain layer
--to some geometry and returns that z value.
--uses radius to search within.
--Variables:
--{{from_layer}} the layer to get a z value for
--{{terrain_layer}} the layer to get a z value from
--{{max_distance}} the maximum distance to search within for a z value (smaller=faster)
--{{id}} the object id (in from_layer) to get a z value for

SELECT ST_Z(t.wkb_geometry) 
FROM {{terrain_layer}} As t, {{from_layer}} As f   
WHERE ST_DWithin( t.wkb_geometry, (ST_Centroid(f.wkb_geometry)) , {{max_distance}}) 
AND f.ogc_fid = {{id}}
ORDER BY ST_Distance(t.wkb_geometry, (ST_Centroid(f.wkb_geometry)))
LIMIT 1;

