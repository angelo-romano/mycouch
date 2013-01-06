# coding: utf8
import csv
import os.path
import sys
import simplejson
from datetime import datetime
from decimal import Decimal
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
        self._way_map = {}
        self._rel_map = {}
        self._way_coord_map = {}
        self._way_coord_nodeset = set()
        self._city_osmid_coords = {}

    def ways(self, ways):
        way_ids = set(self._way_map.keys())
        for this_entry in ways:
            osmid, tags, nodes = this_entry
            if osmid not in way_ids:
                continue
            way_ids.remove(osmid)
            nodes = set(nodes)
            self._way_coord_nodeset.update(nodes)
            for node in nodes:
                self._way_coord_map[node] = self._way_map[osmid]
            if not way_ids:
                break

    def node2(self, nodes):
        for this_entry in nodes:
            osmid, tags, coords = this_entry
            if osmid not in self._way_coord_nodeset:
                continue
            self._way_coord_nodeset.remove(osmid)
            city_osmid = self._way_coord_map[osmid]
            if city_osmid not in self._city_osmid_coords:
                self._city_osmid_coords[city_osmid] = [coords]
            else:
                self._city_osmid_coords[city_osmid].append(coords)
            if not self._way_coord_nodeset:
                break

    def get_cities(self):
        entries_main = self.entries_main
        entries_sub = self.entries_sub
        tuple_avg = lambda *args: (sum([Decimal(x[0]) for x in args]) / Decimal(len(args)),
                                   sum([Decimal(x[1]) for x in args]) / Decimal(len(args)))

        for osmid, entry in self._rel_map.iteritems():
            # time to compute coordinate averages
            coord_list = self._city_osmid_coords.get(osmid)
            if not coord_list:
                continue
            coord = tuple_avg(*coord_list)
            type = entry.pop('type')
            entry['coords'] = coord
            if type == 'town':
                entries_main.append(entry)
            else:
                entries_sub.append(entry)

        return (entries_main, entries_sub)

    def city_tag_filter(self, tags):
        place = tags.get('place')
        if place in self.town_levels:
            return
        if place in self.subtown_levels:
            return
        if place in self.suburb_levels:
            return
        for k in tags.keys():
            del tags[k]

    def relations(self, relations):
        coords = None
        for this_entry in relations:
            osmid, tags, orig_ways = this_entry
            ways = filter(lambda o: o[1] == 'way' and o[2] == 'admin_centre', orig_ways)
            if not ways:
                ways = filter(lambda o: o[1] == 'way' and o[2] == 'outer', orig_ways)
            name = force_str(tags.pop('name')) if 'name' in tags else ''
            place = tags.get('place')
            type = None
            if place in self.town_levels:
                type = 'town'
            if place in self.subtown_levels:
                # if 'is_in' not in tags:
                type = 'town'
                #else:
                #    type = 'subtown'
            elif place in self.suburb_levels:
                type = 'subtown'
            if type:
                self._rel_map[osmid] = {
                    'name': name, 'coords': coords, 'tags': tags, 'type': type}
                for way in ways:
                    self._way_map[way[0]] = osmid

    def nodes(self, nodes):
        for this_entry in nodes:
            osmid, tags, coords = this_entry
            place = tags.get('place')
            name = force_str(tags.pop('name')) if 'name' in tags else ''
            if place in self.town_levels:
                self.entries_main.append({'name': name, 'coords': coords, 'tags': tags})
            if place in self.subtown_levels:
                #if 'is_in' not in tags:
                self.entries_main.append({'name': name, 'coords': coords, 'tags': tags})
                #else:
                #    self.entries_sub.append({'name': name, 'coords': coords, 'tags': tags})
            elif place in self.suburb_levels:
                self.entries_sub.append({'name': name, 'coords': coords, 'tags': tags})


if __name__ == '__main__':
    fname, country_code = os.path.abspath(sys.argv[1]), sys.argv[2]
    # instantiate counter and parser and start parsing
    counter = CityCounter(country_code)
    print '[%s] First parsing phase...' % datetime.now().isoformat()
    p = OSMParser(concurrency=4, nodes_callback=counter.nodes,
                  relations_callback=counter.relations)
                  #nodes_tag_filter=counter.city_tag_filter,
                  #relations_tag_filter=counter.city_tag_filter)
    p.parse(fname)
    print '[%s] Second parsing phase...' % datetime.now().isoformat()
    p = OSMParser(concurrency=4, ways_callback=counter.ways)
    p.parse(fname)
    print '[%s] Third and final parsing phase...' % datetime.now().isoformat()
    p = OSMParser(concurrency=4,
                  nodes_callback=counter.node2)
    p.parse(fname)
    entries_main, entries_sub = counter.get_cities()
    print '[%s] CSV being written now...' % datetime.now().isoformat()

    with open('/tmp/cities-%s.txt' % country_code, 'w') as fh:
        writer = csv.writer(fh)
        added_names = set()
        for this_entry in entries_main:
            name = this_entry.get('name')
            coords = this_entry.get('coords')
            tags = simplejson.dumps(this_entry.get('tags'))
            print name, coords, added_names, (not name), (name in added_names)
            if not name:
                continue
            if name in added_names:
                continue
            writer.writerow([name, country_code, coords[0], coords[1], True, tags])
            added_names.add(name)

        added_names.clear()
        for this_entry in entries_sub:
            name = this_entry.get('name')
            coords = this_entry.get('coords')
            tags = simplejson.dumps(this_entry.get('tags'))
            if name in added_names:
                continue
            writer.writerow([name, country_code, coords[0], coords[1], False, tags])
            added_names.add(name)
