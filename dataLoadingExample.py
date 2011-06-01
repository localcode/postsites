from loader import *

def readFolder():

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


def readConfig():
    # After the xls file has been edited, it needs to be read back in, and then the
    # data should be loaded. This should now be ready to go
    dataDir.readConfig(config_file)

    postgis = DataSource({'user':'postgis','dbname':'mydb','password':'postgres'})

    dataDir.loadAll( postgis )

def loadXls():
    # load everything in
    xlsFile = 'Copy of xls_config_Amigos_De_Los_Rios.xls' # an xls file containing the configuration info
    dbinfo = {'user':'postgis','dbname':'mydb','password':'postgres'}
    loadByXls( xlsFile, dbinfo ) # this would load everything according to the
    # configurations set in the spreadsheet. It would use a default projection,
    # EPSG 3785, which could be overrided with a third argument.

if __name__=='__main__':
    print loadXls()


