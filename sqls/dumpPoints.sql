--Takes the points from one table and dumps
--them into another table. Might need 
--point_layer to be made first.
--Variables:
--{{point_layer}} the layer to dump points into
--{{from_layer}} the layer to dum points from
INSERT INTO 
    {{point_layer}} (wkb_geometry) 
    SELECT 
        (g.gdump).geom 
    FROM ( 
        SELECT 
            ST_DumpPoints({{from_layer}}.wkb_geometry) AS gdump 
        FROM 
            {{from_layer}}
        ) AS g;
