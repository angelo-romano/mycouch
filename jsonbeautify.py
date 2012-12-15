#!/usr/bin/python
# Proper header for a Python script.
import argparse
import simplejson
import os.path
import sys

def main(args):
    filename = os.path.abspath(args.filename)
    if not os.path.isfile(filename):
        raise RuntimeError('%s is not a valid file.' % filename)
    
    orig_file = open(filename, "rb")
    content = simplejson.loads(orig_file.read(), use_decimal=True)
    content = simplejson.dumps(content, use_decimal=True, indent=4)
    orig_file.close()

    with open(filename, "w") as fh:
        fh.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='JSON beautifier.')
    parser.add_argument('filename',type=str,
                        help='a JSON content file')

    args = parser.parse_args()

    main(args)
