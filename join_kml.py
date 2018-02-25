#!/usr/bin/env python3
"""Combine kml files into a single one.

TODO:
* Validate input files.
* Combine document names.
* Preserve default namespace.

"""
from itertools import combinations
from math import sqrt
from re import sub
from sys import argv
from xml.etree.ElementTree import parse

NS = {'og': "http://www.opengis.net/kml/2.2"}


class Coord:

    def __init__(self, raw):
        self.raw = raw
        self.lat, self.lon, self.ele = map(float, raw.split(','))

    def __mod__(self, other):
        lat = (self.lat - other.lat)**2
        lon = (self.lon - other.lon)**2
        return sqrt(lat + lon)

    def __str__(self):
        return self.raw


class File:

    def __init__(self, filename):
        self.filename = filename
        self.tree = parse(filename)
        self.root = self.tree.getroot()
        # Coords
        coordinates = self.root.find('.//og:coordinates', NS)
        coordinates = sub(r'[^\w\,\. ]', '', coordinates.text).strip()
        self.coords = [Coord(x) for x in coordinates.split(' ')]
        # Path
        path = self.root.find('.//og:Placemark/og:name', NS).text
        self.pathname = sub('\s+', ' ', path)

    @property
    def start(self):
        return self.pathname

    @property
    def end(self):
        return self.pathname + "*"

    @property
    def first(self):
        return self.coords[0]

    @property
    def last(self):
        return self.coords[-1]

    @staticmethod
    def combine(comparison):
        xfile, yfile = comparison['files']
        xpoint, ypoint = comparison['points']
        print("combining", xfile.pathname, yfile.pathname)
        coords = []
        if xpoint == xfile.start:
            coords += xfile.coords
        else:
            coords += list(reversed(xfile.coords))
        if ypoint == yfile.end:
            coords += yfile.coords
        else:
            coords += list(reversed(yfile.coords))
        xfile.coords = coords
        xfile.pathname = "({}+{})".format(xpoint, ypoint)
        return xfile

    def save(self, filename):
        coords = ' '.join(str(x) for x in self.coords)
        self.root.find('.//og:coordinates', NS).text = coords
        self.root.find('.//og:Placemark/og:name', NS).text = self.pathname
        self.tree.write(filename)


if __name__ == '__main__':

    files = [File(x) for x in argv[1:]]

    while len(files) > 1:
        comparisons = []
        for x, y in combinations(files, 2):
            key = x.pathname + y.pathname
            comparisons.append({
                'distance': x.last % y.first,
                'files': [x, y],
                'points': [x.start, y.end],
            })
            comparisons.append({
                'distance': x.last % y.last,
                'files': [x, y],
                'points': [x.start, y.start],
            })
            comparisons.append({
                'distance': x.first % y.first,
                'files': [x, y],
                'points': [x.end, y.end],
            })
            comparisons.append({
                'distance': x.first % y.last,
                'files': [x, y],
                'points': [x.end, y.start],
            })
        best, *rest = sorted(comparisons, key=lambda x: x['distance'])
        combined = File.combine(best)
        files = [combined] + [f for f in files if f not in best['files']]

    files[0].save('combined.kml')
