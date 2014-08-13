#!/usr/bin/env python

import gzip
from pipeline import *
import util

config = util.read_config('import')
log = util.config_logging(config)

table = 'area.area'
columns=('area', 'zip', 'po_name', 'geom')
filename = 'bayareadata.gz'
area = 'sfbayarea'
db = util.DB.from_config(config)

log.info('importing file %r to table %r' % (filename, table))

# compose import pipeline
cat(gzip.open(filename)) | skip(head=2, tail=2) | split(sep='|') |\
    transform([lambda r: area, 0, 1, 2]) |\
    join('\t') | load_data(db, table, columns=columns, clean=True)
