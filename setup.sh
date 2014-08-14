#!/usr/bin/env bash

# kill connections
sudo pkill -f tp

# run database scripts
pushd .
cd sql
psql postgres -f database.sql
popd

# import and process inital data
python python/import_area_data.py config.ini
python python/process_scraper_area.py config.ini
