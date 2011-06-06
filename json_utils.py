import json

def handler(obj):
    '''A json encoding handler for odd data types.
    credit is due here:
        http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript/2680060#2680060'''
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError, 'object of type: %s with value %s is not JSON serializable' % (type(obj), repr(obj))

