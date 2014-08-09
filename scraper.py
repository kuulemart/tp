"""
Base classes for scrapers
"""
# -*- coding: utf-8 -*-

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from util import read_config, config_logging

class BaseScraper(object):
    """
    Base scraper class. Provides functionality for config and log management
    and extendable logic for scraping.

    Overwrite method get_work to return sequence of params to loop over and
    pass to get_data.

    Overwrite get_data to return scraped data ready to insert to database
    """
    source_name = ''
    staging_table = ''
    staging_fields = []
    staging_func = ''

    def __init__(self):
        self.config = read_config(self.source_name)
        self.log = config_logging(self.config).getLogger(self.source_name)
        self.db = None

    def callproc(self, name, params):
        """
        Helper function for db function calling
        """
        self.log.debug("calling function: %r with params: %s" % (name, params))
        cur = self.db.cursor()
        cur.callproc(name, params)
        return cur.fetchall()

    def insert_staging_data(self, data):
        """
        Inserts data to staging table. Staging table and fields are defined in
        staging_table and staging_fields attributes. Data dict should contain
        all fields needed for staging table.
        """
        self.log.debug("inserting to table: %s" % self.staging_table)
        cur = self.db.cursor()
        sql = 'insert into %s' % self.staging_table
        sql += '(%s)' % ', '.join(self.staging_fields)
        sql += 'values(%s)' % ', '.join('%%(%s)s'%f for f in self.staging_fields)
        cur.executemany(sql, data)

    def init_staging(self):
        """
        Cleans staging table
        """
        self.log.debug("truncating table: %s" % self.staging_table)
        cur = self.db.cursor()
        cur.execute('truncate table %s' % self.staging_table)

    def process_staging(self):
        """
        Calls staging db function, defined in staging_func attribute
        """
        self.callproc(self.staging_func, [self.source_name])

    def get_work(self):
        """
        Overwrite function to return sequence of params to pass to get_data
        """
        raise NotImplementedError

    def get_data(self, **params):
        """
        Overwrite to return scraped data. Function gets params from sequence
        returned from get_work
        """
        raise NotImplementedError

    def run(self):
        """
        Gets sequence of work params. Iterates over sequence and in each
        iteration cleans staging stable, gets data, inserts it to staging table
        and calls staging function
        """
        try:
            self.db = connect(self.config['db'], cursor_factory=RealDictCursor)

            for params in self.get_work():
                self.init_staging()
                data = self.get_data(**params)
                self.insert_staging_data(data)
                self.process_staging()
                self.db.commit()

        except Exception as e:
            if self.db:
                self.db.rollback()
            self.log.fatal(e)
            raise

        finally:
            if self.db:
                self.db.close()



class BaseVenueScraper(BaseScraper):
    """
    Base class for venue scrapers.

    Defines staging tables and function for venues and functions to get areas
    and categories to scrape venues from.
    """
    staging_table = 'staging.venue'
    staging_fields = [
        'id', 'key_category', 'name', 'lat', 'lng', 'zip', 'address', 'phone'
    ]
    staging_func = 'staging.process_venue'
    area_func = 'scraper.get_venue_area'
    category_func = 'scraper.get_venue_category'

    def get_work(self):
        """
        Reads source categories and areas from db. Returns sequence of params
        for every category in every area.
        """
        categories = self.callproc(self.category_func, [self.source_name])
        for area in self.callproc(self.area_func, [self.source_name]):
            for category in categories:
                yield {
                    "area": area['value'],
                    "category": category['value'],
                    "key_category": category['key_category']
                }
