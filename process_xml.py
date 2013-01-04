import csv
import sys
import simplejson
from xml.dom.minidom import parse
from itertools import chain

class Handler(object):
    @classmethod
    def handle_node(cls, obj, destfile, country):
        resp_list = []
        nodes = obj.getElementsByTagName('node')
        relations = obj.getElementsByTagName('relation')
        with open(destfile, 'w') as fh:
            writer = csv.writer(destfile)
            for node in chain(nodes, relations):
                tags = node.getElementsByTagName('tag')
                entry = {}
                for tag in tags:
                    key = tag.getAttribute('k')
                    val = tag.getAttribute('v')
                    entry[key] = val
                if nodes.tag == 'node':
                    lat = node.getAttribute('lat')
                    lon = node.getAttribute('lon')
                name = entry.pop('name')
                writer.writerow([name, country, lat, lon,
                                 simplejson.dumps(resp_list)])


def main(country):
    orig_file = '/tmp/%s.xml' % country
    dest_file = '/tmp/%s.json' % country
    dom = parse(orig_file)
    Handler.handle_node(dom, dest_file, country)


if __name__ == '__main__':
    main(sys.argv[1])
