#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import re
import urllib
import json
from bottle import install, get, request, response, run, HTTPError
import bottle_pgpool
import psycopg2.pool
import util

### API endpoints


api_v1 = '/api/v1'
ep = util.AttrDict(
    index = os.path.join(api_v1, 'index'),
    venues = os.path.join(api_v1, 'venues'),
    venue = os.path.join(api_v1, 'venues/<id:int>'),
    venue_nearby = os.path.join(api_v1, 'venues/<id:int>/nearby'),
    categories = os.path.join(api_v1, 'categories'),
    category = os.path.join(api_v1, 'categories/<id:int>'),
    category_venues = os.path.join(api_v1, 'categories/<id:int>/venues'),
    zips = os.path.join(api_v1, 'zips'),
    zip = os.path.join(api_v1, 'zips/<zip>'),
    zip_venues = os.path.join(api_v1, 'zips/<zip>/venues'),
)


### setup


config = util.read_config("api")
log = util.config_logging(config).getLogger("server")
# connection pool
pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=int(config.max_connections or 10),
    dsn=config.db,
    cursor_factory=psycopg2.extras.RealDictCursor
)
# install plugin
install(bottle_pgpool.PgSQLPoolPlugin(pool))


###  helpers


def fq_url(*path, **subst):
    """
    Builds fully qualified url. Uses bottle request object for scheme and loc
    info and works only within request
    """
    return re.sub(
        r'<([^:>]+)[^>]*>',
        r'{\1}',
        urllib.basejoin(
            "{scheme}://{netloc}".format(
                scheme=request.urlparts.scheme,
                netloc=request.urlparts.netloc),
            os.path.join(*path))
    ).format(**subst)


def href(url, **attrs):
    """
    Builds hypermedia reference with href url and attributes
    """
    return dict(attrs, href=url)


def get_limit():
    """
    Result item count limit.
    If not specified in query, set it to default (100). Should be less or equal
    than max_limit (100)
    """
    return min(
        int(request.query.getone('limit', config.getint('default_limit', 100))),
        config.getint('max_limit', 100)
    )


def http_assert(is_true, *p, **kw):
    if not is_true:
        raise HTTPError(*p, **kw)


class Linker:
    """
    Decorates data with hypermedia links
    """

    # link definitions:
    #   dict with key = data type and value = function returning dict with links
    _links = {
        "index": lambda item: {
            "self": href(request.url),
            "index": href(fq_url(ep.index)),
            "venues": href(
                fq_url(ep.venues),
                params=["zip", "key_category", "location", "radius", "limit"]
            ),
            "categories": href(
                fq_url(ep.categories),
                params=["limit"]
            ),
            "zips": href(
                fq_url(ep.zips),
                params=["limit"]
            )
        },
        "zips": lambda item: {
            "self": href(fq_url(ep.zip, zip=item['zip'])),
            "zip_venues": href(
                fq_url(ep.zip_venues, zip=item['zip']),
                params=["key_category", "location", "radius", "limit"]
            ),
        },
        "categories": lambda item: {
            "self": href(fq_url(ep.category, id=item['id'])),
            "category_venues": href(
                fq_url(ep.category_venues, id=item['id']),
                params=["zip", "location", "radius", "limit"]
            ),
        },
        "venues": lambda item: {
            "self": href(fq_url(ep.venue, id=item['id'])),
            "category": href(fq_url(ep.category, id=item['key_category'])),
            "zip": href(fq_url(ep.zip, zip=item['zip'])),
            "nearby": href(
                fq_url(ep.venue_nearby, id=item['id']),
                params=["zip", "key_category", "radius", "limit"]
            ),
        },
    }

    def _create_linker(self, func):
        """
        Returns linker function that updates "_links" in data dict with result
        of given link function
        """
        def linker(item):
            item.setdefault("_links", {}).update(func(item))
            return item
        return linker

    def index(self, data):
        """
        Main index links, added to every result
        """
        linker = self._create_linker(self._links["index"])
        return linker(data)

    def __getattr__(self, name):
        """
        Dynamic linker function
        """
        def func(data):
            http_assert(data is not None, 404, 'Not found')
            linker = self._create_linker(self._links[name])
            if isinstance(data, (list, tuple)):
                return self.index({
                    name: map(linker, data),
                    'item_count': len(data),
                    'limit': get_limit()
                })
            return self.index(linker(data))
        return func

linker = Linker()


### routes


@get(ep.categories)
@get(ep.category, autocommit=1)
def categories_handler(db, id=None):
    q = util.Query(db, """
        select id, name
        from venue.category
        where 1 = 1
    """)
    if id is not None:
        q.add("and id = %(id)s", params=dict(id=id))
        data = q.first()
    else:
        # limit results
        q.add("limit %(limit)s", params=dict(limit=get_limit()))
        data = q()
    return linker.categories(data)


@get(ep.venues)
@get(ep.venue)
def venues_handler(db, id=None):
    q = util.Query(db, """
        select v.id, v.name, v.zip, v.address, v.phone, v.key_category
             , ST_AsGeoJSON(v.loc) as location
             , c.name as category
        from venue.venue v
        join venue.category c on v.key_category = c.id
        where 1 = 1
    """,)
    # convert location string to json
    q.map['location'] = util.geojson_to_lng_lat_dict
    if id is not None:
        q.add("and v.id = %(id)s", params=dict(id=id))
        data = q.first()
    else:
        params = request.query
        # zip filter
        if 'zip' in params:
            q.add("and v.zip = any(%(zip_arr)s)")
            q.params["zip_arr"] = str(params['zip']).split(',')
        # category filter
        if 'key_category' in params:
            q.add("and v.key_category = any(%(key_category_arr)s)")
            q.params["key_category_arr"] = map(int, str(params['key_category']).split(','))
        # location & radius filter
        if 'location' in params and 'radius' in params:
            location = params['location'].split(',')
            q.add("""
                and ST_Distance_Sphere(
                        v.loc,
                        --ST_SetSRID(ST_Point(%(lng)s, %(lat)s), 4326)
                        ST_Point(%(lng)s, %(lat)s)
                    ) <= %(radius)s
            """)
            q.params.update(
                lng=float(location[0]),
                lat=float(location[1]),
                radius=float(params['radius'])
            )
        # limit results
        q.add("limit %(limit)s", params=dict(limit=get_limit()))
        data = q()
    # return linked data as json
    return linker.venues(data)


@get(ep.venue_nearby)
def venue_nearby_handler(db, id):
    params = request.query.dict
    # get venue location as geojson
    q = util.Query(db, """
        select ST_AsGeoJSON(loc) as loc
        from venue.venue
        where id = %(id)s
    """)
    q.map['loc'] = util.geojson_to_point
    row = q.first(id = id)
    http_assert(row, 404, 'Not found')
    loc = row['loc']
    params.update(location = [loc])
    # default radius is 1km
    params.setdefault('radius', [1000])
    return venues_handler(db)


@get(ep.category_venues)
def category_venues_handler(db, id):
    params = request.query.dict
    params.update(key_category=[id])
    return venues_handler(db)


@get(ep.zip_venues)
def zip_venues_handler(db, zip):
    params = request.query.dict
    params.update(zip=[zip])
    return venues_handler(db)


@get(ep.zips)
@get(ep.zip)
def zips_handler(db, zip=None):
    if zip is not None:
        data = {"zip": zip}
    else:
        q = util.Query(db, """
            select distinct zip from venue.venue
        """)
        # limit results
        q.add("limit %(limit)s", params=dict(limit=get_limit()))
        data = q()
    return linker.zips(data)


@get(ep.index)
def index():
    return linker.index({})


### start


run(
    host=config.address or '0.0.0.0',
    port=config.port or '8080',
    reloader=config.reloader,
    #debug=True
)
