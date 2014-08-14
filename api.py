#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import re
import urllib
import json
import bottle
import bottle_pgpool
import psycopg2.pool
import util


### API endpoints


api_v1 = '/api/v1'
ep = util.AttrDict(
    index = os.path.join(api_v1, 'index'),
    categories = os.path.join(api_v1, 'categories'),
    category = os.path.join(api_v1, 'categories/<id_category:int>'),
    venues = os.path.join(api_v1, 'venues'),
    venue = os.path.join(api_v1, 'venues/<id_venue:int>'),
    venue_nearby = os.path.join(api_v1, 'venues/<id_venue:int>/nearby'),
    category_venues = os.path.join(api_v1, 'categories/<id_category:int>/venues'),
    zip_venues = os.path.join(api_v1, 'zips/<id_zip>/venues'),
    zips = os.path.join(api_v1, 'zips'),
    zip = os.path.join(api_v1, 'zips/<id_zip>'),
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
# init bottle
app = bottle.Bottle()
app.install(bottle_pgpool.PgSQLPoolPlugin(pool))


### hypermedia helpers


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
                scheme=bottle.request.urlparts.scheme,
                netloc=bottle.request.urlparts.netloc),
            os.path.join(*path))
    ).format(**subst)


def href(url, **attrs):
    """
    Builds hypermedia reference with href url and attributes
    """
    return dict(attrs, href=url)


class Linker:
    """
    Decorates data with hypermedia links
    """

    # link definitions:
    #   dict with key = data type and value = function returning dict with links
    _links = {
        "index": lambda item: {
            "self": href(bottle.request.url),
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
            "self": href(fq_url(ep.zip, id_zip=item['zip'])),
            "zip_venues": href(fq_url(ep.zip_venues, id_zip=item['zip']))
        },
        "categories": lambda item: {
            "self": href(fq_url(ep.category, id_category=item['id'])),
            "category_venues": href(fq_url(ep.category_venues, id_category=item['id'])),
        },
        "venues": lambda item: {
            "self": href(fq_url(ep.venue, id_venue=item['id'])),
            "category": href(fq_url(ep.category, id_category=item['key_category'])),
            "zip": href(fq_url(ep.zip, id_zip=item['zip'])),
            "nearby": href(
                fq_url(ep.venue_nearby, id_venue=item['id']),
                params=["key_category", "radius", "limit"]
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
        def func(data, single=True):
            linker = self._create_linker(self._links[name])
            if not single:
                return self.index({
                    name: map(linker, data),
                    'item_count': len(data),
                })
            if isinstance(data, (list, tuple)):
                data = data[0]
            return self.index(linker(data))
        return func

linker = Linker()


###  result data formatter


# currently only json is supported
def result(data):
    bottle.response.content_type = 'application/json; charset=UTF-8'
    return json.dumps(data)


### routes


@app.route(ep.categories)
@app.route(ep.category)
def categories_handler(db, id_category=None):
    q = util.Query(db, """
        select id, name
        from venue.category
        where 1 = 1
    """)
    q.add("and id = %(id)s", id_category)
    # limit results
    if not id_category:
        params = bottle.request.query
        limit = int(params.get('limit', config.get('default_limit', 100)))
        q.add("limit %(limit)s", limit > 0)
        q.params.update(limit=limit)

    return result(
        linker.categories(q(id=id_category), id_category)
    )


@app.route(ep.venue_nearby)
def venue_nearby_handler(db, id_venue):
    params = bottle.request.query.dict
    # get venue location as geojson
    q = util.Query(db, """
        select ST_AsGeoJSON(loc) as loc
        from venue.venue
        where id = %(id_venue)s
    """)
    q.map['loc'] = util.geojson_to_point
    loc = q(id_venue = id_venue)[0]['loc']
    params.update(location = [loc])
    # default radius is 1km
    params.setdefault('radius', [1000])
    return venues_handler(db)

@app.route(ep.venues)
@app.route(ep.venue)
@app.route(ep.category_venues)
@app.route(ep.zip_venues)
def venues_handler(db, id_venue=None, id_category=None, id_zip=None):
    q = util.Query(db, """
        select v.id, v.name, v.zip, v.address, v.phone, v.key_category
             , ST_AsGeoJSON(v.loc) as location
             , c.name as category
        from venue.venue v
        join venue.category c on v.key_category = c.id
        where 1 = 1
    """)
    q.add("and v.id = %(id_venue)s", id_venue)
    q.add("and c.id = %(id_category)s", id_category)
    q.add("and v.zip = %(id_zip)s", id_zip)

    #params = params or bottle.request.query.dict
    params = bottle.request.query
    # zip
    if 'zip' in params:
        q.add("and v.zip = any(%(zip_arr)s)")
        q.params["zip_arr"] = params['zip'].split(',')
    # category
    if 'key_category' in params:
        q.add("and v.key_category = any(%(key_category_arr)s)")
        q.params["key_category_arr"] = map(int, params['key_category'].split(','))
    # location & radius
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
    if not id_venue:
        limit = int(params.get('limit', config.get('default_limit', 100)))
        q.add("limit %(limit)s", limit > 0)
        q.params.update(limit=limit)
    # convert location string to json
    q.map['location'] = util.geojson_to_lng_lat_dict
    # return linked data as json
    return result(
        linker.venues(
            q(
                id_venue=id_venue,
                id_category=id_category,
                id_zip=id_zip
            ),
            id_venue
        )
    )


@app.route(ep.zips)
@app.route(ep.zip)
def zips_handler(db, id_zip=None):
    if id_zip:
        zips = [{"zip": id_zip}]
    else:
        q = util.Query(db, """
            select distinct zip from venue.venue
        """)
        # limit results
        params = bottle.request.query
        limit = int(params.get('limit', config.get('default_limit', 100)))
        q.add("limit %(limit)s", limit > 0)
        q.params.update(limit=limit)
        zips = q()
    return result(
        linker.zips(zips, id_zip)
    )


@app.route(ep.index)
def index():
    return result(linker.index({}))


### start


app.run(
    host=config.address or '0.0.0.0',
    port=config.port or '8080',
    reloader=config.reloader,
    debug=True
)
