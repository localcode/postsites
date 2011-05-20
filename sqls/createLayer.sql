--Creates a new layer in a POstGIS database
--with an ogc_fid attribute
--Variables:
--{{layer_name}}
CREATE TABLE {{layer_name}} ( 
  ogc_fid serial NOT NULL
);
