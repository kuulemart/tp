#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scraper import BaseVenueScraper
import foursquare
import json

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

    def __init__(self):
        super(FSVenueScraper, self).__init__()
        self.fs = foursquare.Foursquare(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret']
        )
        # build category cache
        self._cats = self.get_cats()

    def get_data(self, area, category, key_category):
        area_dict = json.loads(area)
        category_list = json.loads(category)
        self.log.debug("area: %s" % area_dict)
        self.log.debug( "category: %s" % category_list)
        params = dict(intent='browse')
        params.update(area_dict)
        params.update(categoryId=self.get_cat_id(category_list))
        data = self.fs.venues.search(params=params)
        return self.transform_data(data, key_category=key_category)


if __name__ == '__main__':
    scraper = FSVenueScraper()
    scraper.run()
