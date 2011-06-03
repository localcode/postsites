import os
import sys
from __init__ import *

def clean(rawInput):
    out = rawInput.strip()
    return out

def getXlsFiles(folder):
    a = [os.path.split(m)[1] for m in os.listdir(folder) if os.path.splitext(m)[1] == '.xls']
    if len(a) > 0:
        return a
    else:
        f = 'There are no xls files in this folder'
        m = 'Please enter a different folder'
        return (f + m)




#########################################

def run():

    command = sys.argv[1]


    if command == 'makexls':
        folder = os.path.abspath(sys.argv[2])
        return makeXlsConfigurationFile( folder )

    elif command == 'loadxls':
        print 'Please enter the name of the xls file you would like to load,'
        print 'or the name of the folder where it is located.'
        result = raw_input("or press 'Enter' if it is in this folder:\n%s\n\n" % os.getcwd())
        if result == '': # they said it is in the current directory
            files = getXlsFiles(os.getcwd())
        else:
            files = getXlsFiles(clean(result))

        if not (type(files) == list):
            print files
            return
        elif len(files) == 1:
            yes = raw_input( "If the xls file is '%s', press 'Enter'." % files[0])
            if yes == '':
                xls = files[0]
            else:
                print 'start over'
                return

        elif len(files) > 1:
            print
            print 'I found these files, which one is it?'
            for i in range(len(files)):
                print '%s: %s' % (i+1, files[i])
            print
            n = clean(raw_input("Please enter the number of the correct file."))
            xls = files[n-1]



        print
        print "Now I'll need connection information for the database."
        print
        print 'Be sure that you have created a spatial database in PostgreSQL'
        dbuser = raw_input('Please enter the database user name:\n')
        dbname = raw_input('Please enter the name of the spatial database:\n')
        dbpassword = raw_input('Please enter the password for the database:\n')
        user, db, pw = [clean(i) for i in [dbuser, dbname, dbpassword]]



        print 'Thanks!'
        dbinfo = {'user':user, 'dbname':db, 'password':pw}
        print
        print "Here's you database connection info:\n%s" % dbinfo

        return loadFromXlsConfigurationFile( xls, dbinfo, verbose=True )

run()
