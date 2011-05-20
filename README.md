## PostSites

---

PostSites is a set of python modules for managing PostGIS data sets and retrieving multiple layers of spatial data for a set of sites, represented by the features on a particular layer. It allows one to retrieve multple layers of data based on proximity to a point, and for organizing layers into specific types (such as terrain, parcels, etc.) that can be used for 3d modeling or visualization.


PostSites is being developed as part of the [Local Code](http://vimeo.com/8080630) project under the leadership of [Nicholas de Monchaux](www.nicholas.demonchuax.com), Assistant Professor of Architecture and Urban Design at the [UC Berkeley College of Environmental Design](http://ced.berkeley.edu/).

### Dependencies

PostSites needs [`psycopg2`](http://www.initd.org/psycopg/) and [`simplejson`](http://pypi.python.org/pypi/simplejson/) to be installed and available on `sys.path`. Note that [`simplejson` is included](http://stackoverflow.com/questions/712791/json-and-simplejson-module-differences-in-python) in the standard libraries for python 2.6 and later, as `json`. I'm using `simplejson` for backwards compatibility, so if you want to use python 2.5, you can. `postsites.py` attempts to import `simplejson` first, and if that doesn't work, attempts to import `json`.

---

### Contents

* `layers.py` contains an example dictionary for organizing and managing layers.
* `connection-info.py` is an example of a small configuration dictionary used for connecting to the PostGIS database 
* `sqls` is a folder of sql templates used to build queries
* `plpython` is a folder of functions written in the plpython language for use in PostgreSQL


---

### Example of Use

Disclaimer: I wrote this usage example _before_ I started writing out the code, in order to help me figure out what I _want_ it to do. It will work pretty similar to this.


```python
>>> # get connection info
>>> from configure import dbinfo
>>> # dbinfo is a dictionary with 'user', 'dbname', and 'password' keys
>>> # Make some stuff
>>> from layers import physical, sites
>>> layerDict = dict(physical.items() + sites.items())
>>> config = ConfigurationInfo()
>>> config.layers = dictToLayers(layerDict)
>>> config.siteLayer = 'vacantparcels'
>>> config.terrainLayer = 'terrain'
>>> config.buildingLayer = 'buildings'
>>>
>>> ds = DataSource(dbinfo)
>>> ds.config = config
>>> for layer in ds.config.layers:
>>>     print layer.name, layer.name_in_db, layer.cols
buildings doitt_building_01_28jul2009 ['ogc_fid', 'bin']
transportation doitt_transportation_structure_01_28jul2009 ['ogc_fid']
vacantparcels newyork_parcels ['ogc_fid', 'borough', 'block', 'lot', 'zipcode', 'address', 'landuse', 'ownername', 'lotfront', 'lotdepth', 'assessland', 'assesstot', 'exemptland', 'exempttot']
sidewalks doitt_sidewalk_01_28jul2009 ['ogc_fid']
medians doitt_median_01_28jul2009 ['ogc_fid', 'street_nam']
hydrostructures doitt_hydrography_structure_01_28jul2009 ['ogc_fid']
terrain terrain_points ['ogc_fid']
parkinglots doitt_parking_lot_01_28jul2009 ['ogc_fid']
hydrography doitt_hydrography_01_282009 ['ogc_fid']
paperstreets newyork_paperstreets ['ogc_fid', 'objectid', 'street']
>>>
>>> ds.getSiteJSON( id=200 )
{'Layers':[{'layer':'site', {'type':'Feature', 'geometry': {...}, 'properties':{...}}},
        {'layer':'terrain', {'type':'FeatureCollection':[ ... ]}},
        {'layer':'othersites', 'FeatureCollection':[ ... ]},
        {'layer':'buildings', 'FeatureCollection':[ ... ]}],
        'SiteProperties': {'prop0':'value0', ... }}
>>> ds.getSite( id=190 )
<Site object:'site 190'>
>>> s = Site(ds, id=200)
>>> s2 = Site(ds, query='assess_val = 3000')
>>> s.properties
None
>>> s.build() # retrieves the site data and builds
>>> s.properties
{'prop0':'value0', ... }
>>> s.layers
[<Layer object:'terrain'>, <Layer object:'buildings'>, ... ]
>>> s.prop0
'value0'
>>> layer = s.layers[2]
>>> layer.features
{'FeatureCollection':[ ... ]}

```

### The `sqls.py` module

This module is used to build sql statements for various tasks in postGIS.
It tries to create a layer of abstraction around repetitive sql statements, turning them into functions, and passing variables such as the site layer name, a desired layer, a site radius, a site id into sql statements. It also formats lists of columns into strings to be placed into sql statements. Here's an example:
```python
>>> import sqls
>>> m = sqls.getLayer('parcels', 'buildings', ['jello', 'mello', 'blue'], 764736, 500)
>>> print m  #returns the sql statment below
```
```sql
SELECT
        ST_AsGeoJSON(ST_Translate(buildings.wkb_geometry,
    -ST_X(ST_Centroid(
        (SELECT
            parcels.wkb_geometry
        FROM
            parcels
        WHERE
            parcels.ogc_fid = 764736))),
    -ST_Y(ST_Centroid(
        (SELECT
            parcels.wkb_geometry
        FROM
            parcels
        WHERE
            parcels.ogc_fid = 764736)))
    )) , buildings.jello, buildings.mello, buildings.blue
    FROM
        buildings
    WHERE
        ST_DWithin(buildings.wkb_geometry,
        (SELECT
            parcels.wkb_geometry
        FROM
            parcels
        WHERE
            parcels.ogc_fid = 764736)
        , 500)
```
Note in the example above that I'm using sql to move the returned geometry to the 'origin',
where x=0 and y=0. This is necessary for importing geometry into most 3d modeling programs. The new 'origin' in this case becomes the centroid of the geometry representaing an individual site. For help understanding any of the functions above that begin with `ST_`, consult the [PostGIS documentation](http://postgis.refractions.net/docs/).
