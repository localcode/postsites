## PostSites

---

PostSites is a set of python modules for managing PostGIS data sets and retrieving multiple layers of spatial data for a set of sites, represented by the features on a particular layer. It allows one to retrieve multple layers of data based on proximity to a point, and for organizing layers into specific types (such as terrain, parcels, etc.) that can be used for 3d modeling or visualization.


PostSites is being developed as part of the [Local Code](http!w!7<Mouse>C!x!7<Mouse>C!y!7<Mouse>C!z!7

### Dependencies

PostSites needs [`psycopg2`](http://www.initd.org/psycopg/) and [`simplejson`](http://pypi.python.org/pypi/simplejson/) to be installed and available on `sys.path`. Note that [`simplejson` is included](http://stackoverflow.com/questions/712791/json-and-simplejson-module-differences-in-python) in the standard libraries for python 2.6 and later, as `json`. I'm using `simplejson` for backwards compatibility, so if you want to use python 2.5, you can. `postsites.py` attempts to import `simplejson` first, and if that doesn't work, attempts to import `json`.

On Windows, in order to install third party modules (such as `psycopg2`, `simplejson`, `xlwt`, and `xlrd`) from command line with a tool like `easy_install` or `pip`, you will need to run the 'cmd' program as Administrator. To do this, simply right click on the 'cmd' program icon and select 'Run As Administrator'

On Windows, to install `pip` (which is a tool that makes it very easy to install pythoon packages.), you should visit [this page](http://www.pip-installer.org/en/latest/installing.html#using-the-installer) and download the `get-pip.py` script. You will need to run the installer as administrator. Once you've done that, you can install all the depndencies using the following commands (While running as administrator) using 'cmd'.

```bash
pip install psycopg2
pip install simplejson
pip install xlwt
pip install xlrd
```

---

### Contents

* `layers.py` contains an example dictionary for organizing and managing layers.
* `connection-info.py` is an example of a small configuration dictionary used for connecting to the PostGIS database 
* `sqls` is a folder of sql templates used to build queries
* `plpython` is a folder of functions written in the plpython language for use in PostgreSQL


---

### Examples of Use

Disclaimer: I wrote this usage example _before_ I started writing out the code, in order to help me figure out what I _want_ it to do. It will work pretty similar to this.



First, we'll designate a folder that contains our shapefiles. PostSites will detect
any shapefiles that inside this folder, even if they are nested into other folders.

```python
>>> my_data_folder = 'C:\Users\myusername\Desktop\GIS data'
```

The next command is a utility that makes it easy to configure how
our shapefiles are loaded into the PostGIS database.
It gives you one spreadsheet with all unique spatial reference systems
and another sheet that lets you configure information about each file
as well as letting you define any unknown projections. See the tutorials for
examples of how to edit this file.

```python
>>> import postsites
>>> f = postsites.makeXlsConfigurationFile(my_data_folder)
>>> f
'xls_config_GIS_data.xls' # the name of the resulting file.
```

Once you have edited the 'xls_config_GIS_data.xls' file, you can use it to load
everything into the database ...

```python
>>> dbinfo = {'user':'me', 'dbname':'mydb', 'password':'s3cr3TP455w0rdZ'} # this is needed to connect to the db
>>> ds = postsites.loadFromXlsConfigurationFile( f, dbinfo ) # this may take a while, go get a coffee
>>> ds # ds is a DataSource object that we can use to retrieve and configure site information.
<postsites.DataSource object>
```

Did you like that? Only three steps in order to get from a folder to a thing
that can retrieve sites. Next, we can start getting GeoJSON data for a site like this:

```python
>>> mysiteJson = ds.getSiteJson(id=203)
```


### The `sqls.py` module

This module is used to build sql statements for various tasks in postGIS.
It tries to create a layer of abstraction around repetitive sql statements, turning them into functions, and passing variables such as the site layer name, a desired layer, a site radius, a site id into sql statements. It also formats lists of columns into strings to be placed into sql statements.

Here's an example:

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

### The `loader.py` Module

A module for loading data into a PostGIS database for PostSites
Example of Planned Use:

```python
>>> # select a folder to load data from
>>> folder = '/Users/benjamin/projects/localcode/gis_data/'
>>> # use that folder to create a DataDirectory object
>>> dd = DataDirectory(folder)
>>> # see all the unique projections in the directory
>>> dd.uniqueProjections
>>> # See and edit a dictionary of WKT projections and EPSG codes
>>> dd.projectionDictionary
>>> # output a file for adjusting the settings
>>> dd.configureAll()
>>> # load the edited file in order to set up the database correctly
>>> dd.loadConfiguration(config_edited.py)
>>> from postsites import DataSource
>>> ds = DataSource({'user':'postgis','dbname':'mydb','password':'postgres'})
>>> # load all designated files in the directory
>>> dd.loadAll( ds )
>>> # load a particular file, and give it a layer name
>>> dd.loadOne( ds, 'outlines.shp', 'state_outlines')
```

## Some Notes About Spatial Reference Codes:

Two excellent resources for looking up and verifying the EPSG codes for a given
spatial reference are [spatialreference.org](http://spatialreference.org/) and
[prj2epsg.org](http://prj2epsg.org/search). ogr2ogr (the tool used for loading
data in PostSites) is able to read and translate many spatial reference systems
automatically, but it is better to always check your coordinate systems and
ensure that they are transforming _from_ the correct projection _to_ the
correct projection. Additionally, it is common to encounter spatial reference
systems that are unknown or unfamiliar to ogr2ogr's algorithms. In the U.S.,
There are numerous State Plane Projections, and a lot of GIS data is in this
format. Here's an example of a California State Plane projection, used in much of
Los Angeles County's GIS data:

```
PROJCS["NAD_1983_StatePlane_California_V_FIPS_0405_Feet",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",6561666.666666666],PARAMETER["False_Northing",1640416.666666667],PARAMETER["Central_Meridian",-118.0],PARAMETER["Standard_Parallel_1",34.03333333333333],PARAMETER["Standard_Parallel_2",35.46666666666667],PARAMETER["Latitude_Of_Origin",33.5],UNIT["Foot_US",0.3048006096012192]]
```

If we spend some time looking this up at the sites mentioned above, you'll find
the best match is `ESRI:102645`. ogr2ogr does contain this projection in its
list of projections, but it is instead listed as `EPSG:102645`. So when loading
my data using PostSites, I will simply enter `102645` as the EPSG code for any
data layers in this projection.

Some other common projections:

* *EPSG 4326*: WGS 1984, a lat/long geographic coordinate system that extremely common, and the default for all TIGER data. Units in degrees.
* *EPSG 3785*: A Spherical Mercator Projection used in Google Maps and Open Street Maps. Units in meters.
* *EPSG 4269*: North American Datum 1983 Geographic Coordinate System. Units in degrees



