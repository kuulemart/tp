#!/usr/bin/env python

import sys
import gzip
from StringIO import StringIO
from pipeline import *
import util

config = util.read_config('import')
log = util.config_logging(config)

def load_data(db, table, columns=None, clean=True, before=None, after=None):
    def process(pipe):
        try:
            if before:
                before()
            f = StringIO('\n'.join(pipe))
            if clean:
                db.execute('truncate table {table}'.format(table=table))
            db.copy_from(f, table, columns=columns)
            if after:
                after()
            db.connection.commit()
        except:
            db.connection.rollback()
            raise
    return process

# import bayareadata

table = 'area.area'
columns=('area', 'zip', 'po_name', 'geom')
filename = 'bayareadata.gz'
area = 'sfbayarea'
db = util.connect(config)

log.info('importing file %r to table %r' % (filename, table))

cat(gzip.open(filename))|skip(head=2, tail=2)|split(sep='|')|\
    transform([lambda r: area, 0, 1, 2])|\
    join('\t')|load_data(db, table, columns=columns)
