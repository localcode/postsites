## PostSites

---

PostSites is a set of python modules for managing PostGIS data sets and retrieving multiple layers of spatial data for a set of sites, represented by the features on a particular layer. It allows one to retrieve multple layers of data based on proximity to a point, and for organizing layers into specific types (such as terrain, parcels, etc.) that can be used for 3d modeling or visualization.


PostSites is being developed as part of the [Local Code](http://vimeo.com/8080630) project under the leadership of [Nicholas de Monchaux](www.nicholas.demonchuax.com), Assistant Professor of Architecture and Urban Design at the [UC Berkeley College of Environmental Design](http://ced.berkeley.edu/).

### Dependencies

PostSites needs [psycopg2](http://www.initd.org/psycopg/) to be installed, and available on `sys.path`.

---

### Dependencies

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
>>>
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
