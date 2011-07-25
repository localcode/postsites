#!/usr/bin/env python

#add a line eraseme

# standard library modules
import os
import sys

# third party modules
import psycopg2 as pg
import geojson

# package modules
here = os.path.abspath(__file__)
thisDir = os.path.split(here)[0]
parentDir = os.path.split(thisDir)[0]
sys.path.append(parentDir)

import shpPopulate


def connect(dbinfo):
    connString = "user=%(user)s dbname=%(dbname)s password=%(password)s" % dbinfo
    return pg.connect(connString)

def runSQL(connection, directory, file_name):
    c = connection.cursor()
    sql_file = os.path.join(directory, file_name)
    sqlString = open(sql_file, 'r').read()
    c.execute(sqlString)
    data = c.fetchall()
    c.close()
    connection.close()
    return data

class Ogr2Ogr(object):
    def __init__(self, dbinfo=None):
        self.format_out = '-f "GeoJSON"'
        self.sql = self._get_sql()
        self.src_name = self._db_arg(dbinfo)
        self.overwrite = None
        self.srs_out = None
        self.srs_in = None
        self.dest_name = None
        self.zfield = None

    def render(self):
        vars = [
                'ogr2ogr',
                self.sql,
                self.srs_out,
                self.srs_in,
                self.format_out,
                self.overwrite,
                self.dest_name,
                self.src_name,
                self.zfield,
                ]
        return [ v for v in vars if v]

    def _db_arg(self, dbinfo):
        if dbinfo:
            return 'PG:"user=%(user)s dbname=%(dbname)s password=%(password)s"' % dbinfo
        else:
            return None

    def _get_sql(self):
        sql_file = os.path.join(thisDir, 'test.sql')
        sqlString = open(sql_file, 'r').read()[:-1]
        return '-sql "%s"' % sqlString

def makeCall(dbinfo):
    o = Ogr2Ogr(dbinfo)
    return ' '.join(o.render())


def run_command(args, input=None):
    """
    run_command(args, input=None) -> stdoutstring, stderrstring, returncode
    Runs the command, giving the input if any.
    The command is specified as a list: 'ls -l' would be sent as ['ls', '-l'].
    Returns the standard output and error as strings, and the return code"""
    from subprocess import Popen, PIPE
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(input)
    return stdout, stderr, p.returncode

def main(num):

    # get db info
    from amigos import db_info
    c = connect(db_info)
    data = runSQL(c, thisDir, 'test.sql')
    # data is a list of tuples.
    # each tuple contains one feature (therefore, there is no feature collection)

    print data

    #print geojson.loads(str(d), object_hook=geojson.GeoJSON.to_instance)
    #import shpPopulate


    #print dir(shpPopulate)
    #print parentDir
    #print run_command(['ogr2ogr'])

if __name__=='__main__':

    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print "ERROR"
