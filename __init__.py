"""
Local Code

This module is meant to make the process of loading a bunch of shapefiles and
then retrieving data on a per-site basis as painless as possible.
The target audience for PostSites is amateur programmers/designers who are
using scripts in 3d modeling programs or web stuff to import GIS data
in GeoJSON format (a nice, readable, easy to parse format for GIS data that
supports 3D). The package includes utilities that make it easy to load a large
set of shapefiles into a PostGIS database, as well as classes that aid in configuring
how site information is retrieved from that database. This module is intended to retrieve
GeoJSON data for a particular site, organized into a set of layers.

Dependencies:
    PostSites is intended to work with PostGIS (hence the name), and
    therefore expects that a PostGIS database is available, and that both
    PostgreSQL and PostSites are installed. To make calls to the databse,
    it uses psycopg2, and if using python 2.5 or earlier, it needs simplejson
    as well. Additionally, it uses ogr2ogr and ogrinfo, commandline utilities included
    with GDAL for loading and reading data. There are a couple of configuraiton and loading
    scripts that utilize xlwt and xlrd. PostSites should work equally well on Windows
    or Mac.

Examples (disclaimer: still in development)

First, we'll designate a folder that contains our shapefiles. PostSites will detect
any shapefiles that inside this folder, even if they are nested into other folders.

    >>> my_data_folder = 'C:\Users\myusername\Desktop\GIS data'

The next command is a utility that makes it easy to configure how
our shapefiles are loaded into the PostGIS database.
It gives you one spreadsheet with all unique spatial reference systems
and another sheet that lets you configure information about each file
as well as letting you define any unknown projections. See the tutorials for
examples of how to edit this file.

    >>> import postsites
    >>> f = postsites.makeXlsConfigurationFile(my_data_folder)
    >>> f
    'xls_config_GIS_data.xls' # the name of the resulting file.

Once you have edited the 'xls_config_GIS_data.xls' file, you can use it to load
everything into the database ...

    >>> dbinfo = {'user':'me', 'dbname':'mydb', 'password':'s3cr3TP455w0rdZ'} # this is needed to connect to the db
    >>> ds = postsites.loadFromXlsConfigurationFile( f, dbinfo ) # this may take a while, go get a coffee
    >>> ds # ds is a DataSource object that we can use to retrieve and configure site information.
    <postsites.DataSource object>

Next, we can start getting JSON data for a site like this:

    >>> mysiteJson = ds.getSiteJson(id=203)

"""
from core import *
import loader

__all__=[
        'dictToLayers',
        'makeLayerJSON',
        'makeTerrainJSON',
        'ConfigurationInfo',
        'Layer',
        'Site',
        'DataSource',
        'makeXlsConfigurationFile',
        'loadFromXlsConfigurationFile',
        'loader',
        ]
