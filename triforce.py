import scipy
import numpy as np
import shapely
import scipy.spatial as spa
import scipy.spatial.qhull as qhull


def loc(module):
    return str(module.__file__)


def triangulate(pointList):
    """ this function uses a set of 2-dimensional points
    to construct a delaunay triangulation, and returns the
    resulting triplets of indices of points that form
    triangles."""
    points = np.array(pointList, dtype=np.double)
    tri = qhull.Delaunay(points)
    return tri.vertices


if __name__=="__main__":
    print "testing the TRIFORCE!!"
    points = [
            (2.5, 4.6),
            (1.0, 3.5),
            (5.4, 6.7),
            (0.1, 9.0),
            (6.0, 4.5),
            (9.6, 1.2),
            ]

    t = triangulate(points)
    print t
    print t[0]
    for i in t[0]:
        print i
        print points[i]
