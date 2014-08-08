# -*- coding: utf-8 -*-

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
import logging
import sys, os
import __main__
from ConfigParser import SafeConfigParser


class BaseScraper(object):
    source_name = ''
    staging_table = ''
    staging_fields = []
    staging_func = ''

    def __init__(self):
        if len(sys.argv) > 1:
            config_file = sys.argv[1]
        else:
            script = __main__.__file__
            path = os.path.dirname(os.path.abspath(script))
            basename = os.path.splitext(script)[0]
            config_file = os.path.join(path, "%s.ini" % basename)
        cp = SafeConfigParser()
        cp.read(config_file)
        self.config = dict(cp.items(self.source_name))
        self.config_logger(self.config)
        self.log = logging.getLogger(self.source_name)
        self.db = connect(self.config['db'])

    def config_logger(self, config):
        params = {}
        if 'log_file' in config:
            params['filename'] = config['log_file']
        else:
            params['stream'] = sys.stdout
        config.setdefault('log_level', 'info')
        params['level'] = getattr(logging, config['log_level'].upper())
        if 'log_format' in config:
            params['format'] = config['log_format']
        logging.basicConfig(**params)

    def callproc(self, name, params):
        self.log.debug("calling: %s, %s" % (name, params))
        cur = self.db.cursor(cursor_factory=RealDictCursor)
        cur.callproc(name, params)
        return cur.fetchall()

    def insert_staging_data(self, data):
        cur = self.db.cursor()
        sql = 'insert into %s' % self.staging_table
        sql += '(%s)' % ', '.join(self.staging_fields)
        sql += 'values(%s)' % ', '.join('%%(%s)s'%f for f in self.staging_fields)
        cur.executemany(sql, data)

    def init_staging(self):
        cur = self.db.cursor()
        cur.execute('truncate table %s' % self.staging_table)

    def process_staging(self):
        self.callproc(self.staging_func, [self.source_name])

    def get_data(self, **params):
        raise NotImplementedError

    def get_iter(self):
        raise NotImplementedError

    def run(self):
        for param in self.get_iter():
            try:
                self.init_staging()
                data = self.get_data(**param)
                self.insert_staging_data(data)
                self.process_staging()
            except:
                self.db.rollback()
                raise
            self.db.commit()


class BaseVenueScraper(BaseScraper):
    staging_table = 'staging.venue'
    staging_fields = [
        'id', 'key_category', 'name', 'lat', 'lng', 'zip', 'address', 'phone'
    ]
    staging_func = 'staging.process_venue'
    area_func = 'scraper.get_venue_area'
    category_func = 'scraper.get_venue_category'

    def get_iter(self):
        categories = self.callproc(self.category_func, [self.source_name])
        for area in self.callproc(self.area_func, [self.source_name]):
            for category in categories:
                self.log.debug('category: %s' % category)
                self.log.debug('area: %s' % area)
                yield {
                    "area": area['value'],
                    "category": category['value'],
                    "key_category": category['key_category']
                }
