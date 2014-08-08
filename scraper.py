#!/usr/bin/env python
# -*- coding: utf-8 -*-

import foursquare
import collections
from psycopg2 import connect


class BaseScraper:
    source_name = ''
    staging_stable = 'staging.venue'
    staging_fields = [
        'id', 'category', 'name', 'lat', 'lng', 'zip', 'address', 'phone'
    ]
    staging_func = 'staging.process_venue'

    def insert_staging_data(self, data):
        cur = self.db.cursor()
        sql = 'insert into %s' % self.staging_stable
        sql += '(%s)' % ', '.join(self.staging_fields)
        sql += 'values(%s)' % ', '.join('%%(%s)s'%f for f in self.staging_fields)
        cur.executemany(sql, data)

    def init_staging(self):
        cur = self.db.cursor()
        cur.execute('truncate table %s' % self.staging_stable)

    def process_staging(self):
        cur = self.db.cursor()
        cur.callproc(self.staging_func, [self.source_name])

    def get_data(self, area, category):
        raise NotImplementedError

    def run(self, db, area, category_map):
        self.db = db
        self.category_map = category_map
        for cat in category_map:
            try:
                self.init_staging()
                data = self.get_data(area, cat)
                self.insert_staging_data(data)
                self.process_staging()
            except:
                self.db_conn.rollback()
                raise
            self.db_conn.commit()


class BaseVenueScraper(BaseScraper):
    staging_stable = 'staging.venue'
    staging_fields = [
        'id', 'category', 'name', 'lat', 'lng', 'zip', 'address', 'phone'
    ]
    staging_func = 'staging.process_venue'



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

    def get_data(self, area, category):
        params = dict(intent='browse')
        params.update(area)
        cat_4sq = self.category_map[category]
        params.update(categoryId=self.get_cat_id(cat_4sq))
        data = self.fs.venues.search(params=params)
        return self.transform_data(data, category=category)


if __name__ == '__main__':
    # create scraper instance
    CLIENT_ID = 'LNTZ2MKNY53OD00ZLT5QUEXRJHF3NR0FZ0B5KAPJJGS2CVGO'
    CLIENT_SECRET = 'P3I0PMY3IABWAEDGS1G4J24YAOBYXCUYISP0YYT4ZNE0RHEN'
    DB = connect('dbname=tp')

    scraper = FSVenueScraper(DB, CLIENT_ID, CLIENT_SECRET)

    # define scraping area:
    #   SF bay area using bounding box
    area = {
        'ne': '38.864300,-121.208199',
        'sw': '36.893089,-123.533684'
    }

    # category map for converting internal category to 4sq category hierarchy
    category_map = {
        'Cafe': (u'Food', u'Café'),
        'Gym': (u'Shop & Service', u'Gym / Fitness Center')
    }

    # run scraper for all categories in area
    scraper.run(area=area, category_map=category_map)
