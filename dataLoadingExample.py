from loader import *

folder = '/a/path/to/some/folder'

dataDir = DataDirectory(folder)

# This will output the unique projections in nice, readable form.
dataDir.printProjections()

# This shoud take an optional file path argument.
# if none is supplied, it should create a file called xls_config_foldername.xls
# in the current directory.
config_file = dataDir.makeXlsConfig()
print config_file

# STOP


# After the xls file has been edited, it needs to be read back in, and then the
# data should be loaded. This should now be ready to go
dataDir.readConfig(config_file)

postgis = DataSource({'user':'postgis','dbname':'mydb','password':'postgres'})

dataDir.loadAll( postgis )

