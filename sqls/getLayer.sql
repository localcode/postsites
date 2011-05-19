SELECT
    ST_AsGeoJSON(wkb_geometry), {{cols}}
FROM
    {{table}}
WHERE
    ogc_fid={{id}}
;
