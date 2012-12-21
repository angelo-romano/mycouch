import os
import os.path
import sys
import subprocess
import unittest
import tempfile

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from flask.ext.sqlalchemy import SQLAlchemy
from mycouch import app, db
import psycopg2


DATABASE_CONFIG = {
    'username': 'angelo',
    'password': 'ciaobella',
    'host': '127.0.0.1',
    'port': '5432',
    'dbname': 'mycouch_test',
    'dbrole': 'angelo',
}

def setup_database():
    commands = """
    createdb -E UNICODE %(dbname)s
    createlang plpgsql %(dbname)s
    psql -d %(dbname)s -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
    psql -d %(dbname)s -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
    psql %(dbname)s -c "create extension hstore; grant all on database %(dbname)s to %(dbrole)s; grant all on spatial_ref_sys to %(dbrole)s; grant all on geometry_columns to %(dbrole)s;"
    """

    commands = filter(None, [o.strip() for o in commands.split('\n')])
    for this_command in commands:
        this_command = this_command % DATABASE_CONFIG
        this_command = this_command.split(' ')
        print this_command
        subprocess.call(this_command)


def prepare_database():
    db_conn = psycopg2.connect(
        dbname='template1',
        user=DATABASE_CONFIG['username'],
        password=DATABASE_CONFIG['password'],
        port=DATABASE_CONFIG['port'],
        host=DATABASE_CONFIG['host'])
    db_conn.autocommit = True
    cur = db_conn.cursor()
    cur.execute('DROP DATABASE %s;' % DATABASE_CONFIG['dbname'])
    cur.execute('CREATE DATABASE %s TEMPLATE mycouch_template;'
        % DATABASE_CONFIG['dbname'])
    db_conn.close()
