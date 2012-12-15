#!/bin/bash
# To be executed with postgres user (sudo su postgres)
DATABASE_ROLE=$1
DATABASE_NAME=$2
createdb -E UNICODE ${DATABASE_NAME}
createlang plpgsql ${DATABASE_NAME}
psql -d ${DATABASE_NAME} -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -d ${DATABASE_NAME} -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
# Grant permissions to user on the new database
psql ${DATABASE_NAME} -c "create extension hstore; grant all on database ${DATABASE_NAME} to ${DATABASE_ROLE}; grant all on spatial_ref_sys to ${DATABASE_ROLE}; grant all on geometry_columns to ${DATABASE_ROLE};"
