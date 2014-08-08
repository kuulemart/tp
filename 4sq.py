#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scraper import BaseVenueScraper
import foursquare
import json

# Foursquare venue scraper

class FSVenueScraper(BaseVenueScraper):
    source_name = '4sq'

    def __init__(self):
        # init base
        super(FSVenueScraper, self).__init__()
        # create 4sq api wrapper object
        self.fs = foursquare.Foursquare(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret']
        )
        # build category cache
        self._categories = self.get_categories()

    def get_categories(self):
        def proc(data, cats={}):
            for cat in data.get('categories', []):
                cats[cat['name']] = proc(cat, {'id': cat['id']})
            return cats
        return proc(self.fs.venues.categories())

    def get_category_id(self, cat):
        cats = self._categories
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

    def get_data(self, area, category, key_category):
        area_dict = json.loads(area)
        category_list = json.loads(category)
        params = dict(
            area_dict,
            intent='browse',
            limit=self.config.get("venue_limit", '100'),
            categoryId=self.get_category_id(category_list)
        )
        data = self.fs.venues.search(params=params)
        return self.transform_data(data, key_category=key_category)


if __name__ == '__main__':
    scraper = FSVenueScraper()
    scraper.run()
