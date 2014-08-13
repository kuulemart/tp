#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Foursquare venue scraper
"""

from scraper import BaseVenueScraper
import foursquare
import json

# Foursquare venue scraper

class Scraper_4SQVenues(BaseVenueScraper):
    source_name = '4sq'

    def __init__(self):
        """
        Initialises foursquare api library and reads categories
        """
        # init base
        super(Scraper_4SQVenues, self).__init__()
        # create 4sq api wrapper object
        self.fs = foursquare.Foursquare(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret']
        )
        # build category cache
        self._categories = self.get_categories()

    def get_categories(self):
        """
        Queries foursquare categories and builds hierarchical structure of dicts
        containing category name and id as keys for faster navigation
        """
        def proc(data, cats={}):
            for cat in data.get('categories') or []:
                cats[cat['name']] = proc(cat, {'_id': cat['id']})
            return cats
        return proc(self.fs.venues.categories())

    def get_category_id(self, cat):
        """
        Finds category id.
        param cat is list of hierarchical category names
        """
        cats = self._categories
        for name in cat:
            cats = cats[name]
        return cats['_id']

    def transform_data(self, data, **kw):
        for venue in data.get('venues') or []:
            row = dict.fromkeys(self.staging_fields)
            loc = venue['location']
            row.update(
                id=venue['id'],
                name=venue['name'],
                lat=loc['lat'],
                lng=loc['lng'],
                zip=loc.get('postalCode'),
                address=' '.join(loc.get('formattedAddress', [])),
                phone=venue['contact'].get('formattedPhone')
            )
            row.update(kw)
            yield row

    def get_data(self, area, category, key_category):
        self.log.info("scraping area: %s, category: %s" % (area, category))
        category_id = self.get_category_id(json.loads(category))
        self.log.debug("categoryId: %s" % category_id)
        params = dict(
            json.loads(area),
            intent='browse',
            limit=self.config.get("venue_limit", '100'),
            categoryId=category_id
        )
        data = self.fs.venues.search(params=params)
        self.log.info("%s venues found" % len(data.get("venues", [])))
        return self.transform_data(data, key_category=key_category)


if __name__ == '__main__':
    scraper = Scraper_4SQVenues()
    scraper.run()
