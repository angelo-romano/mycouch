# coding: utf8
import os.path
import sys
from imposm.parser import OSMParser
from strings import force_unicode, force_str

# simple class that handles the parsed OSM data.
_tags = set()


class CityCounter(object):
    cnt = 0
    town_levels = [
        'city', 'town']
    subtown_levels = [
        'village']
    suburb_levels = [
        'hamlet', 'suburb', 'neighbourhood']
    entries_main = None
    entries_sub = None

    def __init__(self, country_code):
        self.country_code = country_code
        self.entries_main = []
        self.entries_sub = []

    def relations(self, ways):
        global _tags
        # callback method for ways
        for this_entry in ways:
            osmid, tags, coords = this_entry
            name = force_str(tags.get('name'))# or tags.get('name:en') or u'')
            place = tags.get('place')
            if name.startswith('Ellange'):
                print tags, coords
            if place in self.town_levels:
                self.entries_main.append((('name', name), ('coords', coords)))
            if place in self.subtown_levels:
                if 'is_in' not in tags:
                    self.entries_main.append((('name', name), ('coords', coords)))
                else:
                    self.entries_sub.append((('name', name), ('coords', coords)))
            elif place in self.suburb_levels:
                self.entries_sub.append((('name', name), ('coords', coords)))

    def nodes(self, ways):
        global _tags
        # callback method for ways
        for this_entry in ways:
            osmid, tags, coords = this_entry
            place = tags.get('place')
            name = force_str(tags.get('name'))# or tags.get('name:en') or u'')
            if name.startswith('Ellange'):
                print tags, coords
            if place in self.town_levels:
                self.entries_main.append((('name', name), ('coords', coords)))
            if place in self.subtown_levels:
                if 'is_in' not in tags:
                    self.entries_main.append((('name', name), ('coords', coords)))
                else:
                    self.entries_sub.append((('name', name), ('coords', coords)))
            elif place in self.suburb_levels:
                self.entries_sub.append((('name', name), ('coords', coords)))


if __name__ == '__main__':
    fname, country_code = os.path.abspath(sys.argv[1]), sys.argv[2]
    # instantiate counter and parser and start parsing
    counter = CityCounter(country_code)
    p = OSMParser(concurrency=4, nodes_callback=counter.nodes,
                  relations_callback=counter.relations)
    p.parse(fname)
