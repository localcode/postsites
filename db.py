import psycopg2 as pg
import os
dbname = 'spatial_databank'
user = 'postgres'
pword = 'secret_passwordz'
dbInfo = 'PG:dbname=%s user=%s password=%s' % (dbname, user, pword)
"""
Example Usage:
    >>> import db
    >>> c = db.connect()
    >>> command = db.sqlFromFile('someFileWithOnlySQL.txt', c)
    >>> c.close()
"""

def dbOut(output_type, dest_fileName='', sql='', where='', outSRID=''):
    """
    >>> dbOut('ESRI Shapefile', 'streets.shp')
    """
    dbInfo = '"PG:dbname=%s user=%s password=%s"' % (dbname, user, pword)
    if sql != '':
        sql = ' -sql "'+sql+'"'
    if outSRID != '':
        outSRID = ' -t_srs "'+outSRID+'"'
    if where != '':
        where = ' where="'+where+'"'
    if dest_fileName != '':
        dest_fileName = ' '+dest_fileName
    output_type = ' -f "%s"' % (output_type)
    dbInfo = ' '+dbInfo
# [-where restricted_where] [-sql <sql statement>] [-t_srs srs_def] [-f format_name] [-overwrite] dst_datasource_name src_datasource_name [layer [layer ...]]
    s = 'ogr2ogr%s%s%s%s%s -overwrite%s' % (where, sql, outSRID, output_type, dest_fileName, dbInfo)
    return s
    # os.system(s)

def shpOut(sql='', filePath='out.shp'):
    s = dbOut('ESRI Shapefile', filePath, sql)
    return s

class dbGetter(object):
    def __init__(self, sql):
        self.sql = sql
        
    def shp(self, fileName):
        pass

    def geoJSON(self, fileName):
        pass

    def csv(self, fileName):
        pass

    def kml(self, fileName):
        pass

def connect():
    """Connects to the database and returns a connection object."""
    connectionString = "dbname=%s user=%s password=%s" % (dbname, user, pword)
    conn = pg.connect(connectionString)
    return conn
    
def sqlFromFile(file, connection):
    """this function simply reads a file and executes it
    as sql. it returns the string exactly as it was
    sent to postgres."""
    sql = open(file, 'r').read()
    cursor = connection.cursor()
    out = cursor.mogrify(sql)
    cursor.execute(sql)
    connection.commit()
    cursor.close()
    return out

def getAll(table):
    c = connect()
    cur = c.cursor()
    # following method for constructing SQL
    # is considered SUPER BAD by psycopg,
    # but unfortunately they do not allow 
    # table names to be passed in as variables
    # and therefore this is a sketchy workaround using
    # python string formatting.
    sql = "SELECT * FROM %s;" % table
    cur.execute(sql)
    records = cur.fetchall()
    cur.close()
    c.close()
    return records

def getOne(site_id, table):
    c = connect()
    cur = c.cursor()
    sql = "SELECT * FROM %s WHERE ogc_fid = %s;" % (table, site_id)
    cur.execute(sql)
    records = cur.fetchall()
    cur.close()
    c.close()
    return records
    
def removeSRID(ewkt):
    idx = ewkt.find(';') + 1
    return ewkt[idx:]

def run(sql):
    c = connect()
    cur = c.cursor()
    cur.execute(sql)
    records = cur.fetchall()
    cur.close()
    c.close()
    return records

def runopen(connection, sql):
    cur = connection.cursor()
    cur.execute(sql)
    records = cur.fetchall()
    cur.close()
    return records

def runVoid(sql):
    c = connect()
    cur = c.cursor()
    cur.execute(sql)
    cur.close()
    c.close()
    return 'complete'

if __name__=='__main__':
    
    query = open('getContourPoints.sql', 'r').read()
    dest = 'C:\\Users\\gallery\\LocalCodeNY\\terrainPts.shp'
    cmd = shpOut(query, dest)
    print cmd
    
    

