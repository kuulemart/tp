#!/usr/bin/env python
# -*- coding: utf-8 -*-

import foursquare
import string
import json
from psycopg2 import connect
from psycopg2.extras import RealDictCursor

class BaseScraper:
    source_name = ''
    staging_table = ''
    staging_fields = []
    staging_func = ''

    def callproc(self, name, params):
        print "calling: %s, %s" % (name, params)
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

    def run(self, db):
        self.db = db
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
                print category
                print area
                yield {
                    "area": area['value'],
                    "category": category['value'],
                    "key_category": category['key_category']
                }



# Foursquare venue scraper

class FSVenueScraper(BaseVenueScraper):
    source_name = '4sq'

    def get_cats(self):
        def proc(data, cats={}):
            for cat in data.get('categories', []):
                cats[cat['name']] = proc(cat, {'id': cat['id']})
            return cats
        return proc(self.fs.venues.categories())

    def get_cat_id(self, cat):
        cats = self._cats
        for name in cat:
            cats = cats[name]
        return cats['id']

    def transform_data(self, data, **kw):
        for venue in data.get('venues', []):
            row = dict.fromkeys(self.staging_fields)
            loc = venue['location']
            row.update(
                id=venue['id'],
                name=venue['name'],
                lat=loc['lat'],
                lng=loc['lng'],
                zip=loc['postalCode'],
                address=' '.join(loc.get('formattedAddress', [])),
                phone=venue['contact'].get('formattedPhone')
            )
            row.update(kw)
            yield row

    def __init__(self, client_id, client_secret):
        self.fs = foursquare.Foursquare(
            client_id=client_id,
            client_secret=client_secret
        )
        # build category cache
        self._cats = self.get_cats()

    def get_data(self, area, category, key_category):
        area_dict = json.loads(area)
        category_list = json.loads(category)
        print area_dict
        print category_list
        params = dict(intent='browse')
        params.update(area_dict)
        params.update(categoryId=self.get_cat_id(category_list))
        data = self.fs.venues.search(params=params)
        return self.transform_data(data, key_category=key_category)


if __name__ == '__main__':
    # create scraper instance
    CLIENT_ID = 'LNTZ2MKNY53OD00ZLT5QUEXRJHF3NR0FZ0B5KAPJJGS2CVGO'
    CLIENT_SECRET = 'P3I0PMY3IABWAEDGS1G4J24YAOBYXCUYISP0YYT4ZNE0RHEN'
    DB = connect('dbname=tp')

    # run scraper
    scraper = FSVenueScraper(CLIENT_ID, CLIENT_SECRET)
    scraper.run(DB)
