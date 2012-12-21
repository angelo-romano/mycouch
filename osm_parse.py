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
        'village', 'hamlet']
    suburb_levels = [
        'suburb', 'neighbourhood']

    def relations(self, ways):
        global _tags
        # callback method for ways
        for this_entry in ways:
            osmid, tags, entries = this_entry
            name = force_str(tags.get('name'))# or tags.get('name:en') or u'')
            place = tags.get('place')
            if place in self.town_levels:
                print '1 %s' % name
            if place in self.subtown_levels:
                print '2 %s' % name
            elif place in self.suburb_levels:
                print '3 %s' % name
            #if 'name' in tags and 'Vella' in tags['name']:
            #    print osmid, filter(lambda x: not x.startswith('name'),
            #            tags.keys()), tags['place'], tags['admin_level']
            #_tags = _tags.union(tags)
            self.cnt += 1

    def nodes(self, ways):
        global _tags
        # callback method for ways
        for this_entry in ways:
            osmid, tags, entries = this_entry
            place = tags.get('place')
            name = force_str(tags.get('name'))# or tags.get('name:en') or u'')
            if place in self.town_levels:
                print '1 %s' % name
            if place in self.subtown_levels:
                print '2 %s' % name
            elif place in self.suburb_levels:
                print '3 %s' % name
            #if 'name' in tags and 'Vella' in tags['name']:
            #    print osmid, filter(lambda x: not x.startswith('name'),
            #            tags.keys()), tags['place'], tags['admin_level']
            #_tags = _tags.union(tags)
            self.cnt += 1

if __name__ == '__main__':
    fname = os.path.abspath(sys.argv[1])
    # instantiate counter and parser and start parsing
    counter = CityCounter()
    p = OSMParser(concurrency=4, nodes_callback=counter.nodes,
            relations_callback=counter.relations)
    p.parse(fname)

    # done
    print counter.cnt
    #for t in sorted(list(_tags)):
