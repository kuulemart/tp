#!/usr/bin/env python

from pprint import pprint
from pipeline import *
import util

config = util.read_config('import')
log = util.config_logging(config)
db = util.DB.from_config(config)

table = 'scraper.venue_area'
columns=('source', 'name', 'value')
filename = 'bayareadata.gz'
source = '4sq'
name = 'SF Bay Area'

sql = """
    select ST_AsGeoJSON(ST_Extent(ST_FlipCoordinates(geom))) as area
    from area.area
    group by zip
"""

cat(db.select(sql)) | tee(pprint) |\
    foreach(lambda row: [source, name, util.geojson_to_area(row['area'])]) |\
    join('\t') | tee(pprint) | load_data(db, table, columns=columns, clean=True)
