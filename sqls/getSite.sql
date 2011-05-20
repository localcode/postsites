--Selects the site in question
--Variables:
--{{site_layer}} the layer used for sites
--{{columns}} the columns to return attribute data from
--{{site_id}} the id of the site in question
--{{site_radius}} the distance from the site to search
SELECT
	ST_AsGeoJSON(ST_Translate({{site_layer}}.wkb_geometry, 
    -ST_X(ST_Centroid(
        (SELECT
            {{site_layer}}.wkb_geometry
        FROM
            {{site_layer}}
        WHERE
            {{site_layer}}.ogc_fid = {{site_id}}))), 
    -ST_Y(ST_Centroid(
        (SELECT
            {{site_layer}}.wkb_geometry
        FROM
            {{site_layer}}
        WHERE
            {{site_layer}}.ogc_fid = {{site_id}})))
    )) {{columns}}
FROM
    {{site_layer}}
WHERE
    {{site_layer}}.ogc_fid = {{site_id}}
