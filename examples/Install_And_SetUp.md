## Installation and Set Up

Using PostSites depends on having a number of tools installed. We are continually trying to reduce the amount of effort necessary to set up PostSites and start working with GIS data, but it takes time to wrap up and automate things which can be technically complex, and to create substitutes for tools that are designed primarily for scientists and engineers. If you have any suggestions on ways to make this process easier, we are interested in hearing them.

Here is an rough overview of the steps:

1. Install PostgreSQL
1. Install PostGIS
1. Install GIS code libraries
1. Set up Python

And once you're finished with the above, here's how you get started with PostSites:

1. Find data. 
1. Load the data into the database. 

The `loader.py` module was created to make it as easy as possible to load your data into the database and to load it correctly. Here is a quick example of how to load and configure an entire folder of shapefiles:

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

When you call the `projectionDictionary` attribute, you should see a dictionary well-known text (wkt) representations and any corresponding EPSG codes that you may have set. If you have not looked up and set EPSG codes, the dictionary will have empty spaces where you can enter these codes. Here's an example of one of these dictionaries, when empty (and formatted for clarity):

```python
{'wkt':'''GEOGCS["GCS_North_American_1983",
    DATUM["North_American_Datum_1983",
        SPHEROID["GRS_1980",6378137.0,298.257222101]],
    PRIMEM["Greenwich",0.0],
    UNIT["Degree",0.0174532925199433]]''',
'epsg':None
'index':1}
```

Notice that the `'epsg'` key is set to a value of `None`. The `'index'` key shows the order in which this projection was found when reading through the folder of files. The value of `'wkt'` may appear very different, and the three different keys may be in any order. 

Next, you should look up the EPSG code for the projection using [spatialreference.org](http://www.spatialreference.org)





2. Set up your sites. 
2. Retrieve a site

After that, you're ready to do whatever you like with your sites. Here's some ideas on other things you can do:

1. Analyze and classify your sites
1. Import your sites into a 3d modeling program
1. Make your sites load faster
2. Put your sites on the Internet
2. Generate infographics about your sites.
3. Edit information about your sites.

