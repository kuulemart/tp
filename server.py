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
import util


### endpoints


api_v1 = '/api/v1'
ep = util.AttrDict(
    index = os.path.join(api_v1, 'index'),
    categories = os.path.join(api_v1, 'categories'),
    category = os.path.join(api_v1, 'categories/<id_category:int>'),
    venues = os.path.join(api_v1, 'venues'),
    venue = os.path.join(api_v1, 'venues/<id_venue:int>'),
    category_venues = os.path.join(api_v1, 'categories/<id_category:int>/venues'),
    zip_venues = os.path.join(api_v1, 'zips/<id_zip>/venues'),
    zips = os.path.join(api_v1, 'zips'),
    zip = os.path.join(api_v1, 'zips/<id_zip>'),
)


### setup


config = util.read_config("api")
log = util.config_logging(config).getLogger("server")
app = bottle.Bottle()
db = util.connection_pool(1, int(config.max_connections or 10), config.db)


### hypermedia helpers


def fq_url(*path, **subst):
    return re.sub(
        r'<([^:>]+)[^>]*>',
        r'{\1}',
        urllib.basejoin(
            "{scheme}://{netloc}".format(
                scheme=bottle.request.urlparts.scheme,
                netloc=bottle.request.urlparts.netloc),
            os.path.join(*path))
    ).format(**subst)

def href(url, **kw):
    return dict(kw, href=url)

def create_linker(func):
    def linker(item):
        item.setdefault("_links", {}).update(func(item))
        return item
    return linker

def index_links(data):
    linker = create_linker(lambda item: dict(
        self = href(bottle.request.url),
        index = href(fq_url(ep.index)),
        venues = href(
            fq_url(ep.venues),
            params=["zip", "key_category", "location", "radius"]
        ),
        categories = href(fq_url(ep.categories)),
        zips = href(fq_url(ep.zips))
    ))
    return linker(data)
    #data.setdefault("_links", {}).update(
    #    self = href(bottle.request.url),
    #    index = href(fq_url(ep.index)),
    #    venues = href(
    #        fq_url(ep.venues),
    #        params=["zip", "key_category", "location", "radius"]
    #    ),
    #    categories = href(fq_url(ep.categories)),
    #    zips = href(fq_url(ep.zips))
    #)
    #return data

def venue_links(data, single=True):
    linker = create_linker(lambda item: dict(
        self = href(fq_url(ep.venue, id_venue=item['id'])),
        category = href(fq_url(ep.category, id_category=item['key_category'])),
        zip = href(fq_url(ep.zip, id_zip=item['zip']))
    ))
    if not single:
        return index_links({"venues": map(linker, data)})
    if isinstance(data, (list, tuple)):
        data = data[0]
    return index_links(linker(data))

def category_links(data, single=True):
    linker = create_linker(lambda item: dict(
        self = href(fq_url(ep.category, id_category=item['id'])),
        category_venues = href(fq_url(ep.category_venues, id_category=item['id']))
    ))
    if not single:
        return index_links({"categories": map(linker, data)})
    if isinstance(data, (list, tuple)):
        data = data[0]
    return index_links(linker(data))

def zip_links(data, single=True):
    linker = create_linker(lambda item: dict(
        self = href(fq_url(ep.zip, id_zip=item['zip'])),
        zip_venues = href(fq_url(ep.zip_venues, id_zip=item['zip']))
    ))
    if not single:
        return index_links({"zips": map(linker, data)})
    if isinstance(data, (list, tuple)):
        data = data[0]
    return index_links(linker(data))


### query builder


class Query:
    def __init__(self, db, sql=None, params=None):
        self.db = db
        self.sql = []
        self.map = {}
        self.params = util.AttrDict(params or {})
        self.add(sql, sql)

    def add(self, sql, condition=True):
        if condition:
            self.sql.append(sql)
        return self

    def get_sql(self):
        return "\n".join(self.sql)

    def __call__(self, **kw):
        params = {}
        params.update(self.params)
        params.update(kw)
        self.db.execute(self.get_sql(), params)
        result = self.db.fetchall()
        map(
            lambda r: r.update((k, f(r[k])) for k,f in self.map.items()),
            result
        )
        return result


### routes


@app.route(ep.categories)
@app.route(ep.category)
@db
def categories(db, id_category=None):
    q = Query(db, """
        select id, name
        from venue.category
        where 1 = 1
    """)
    q.add("and id = %(id)s", id_category)
    return json.dumps(
        category_links(q(id=id_category), id_category)
    )


@app.route(ep.venues)
@app.route(ep.venue)
@app.route(ep.category_venues)
@app.route(ep.zip_venues)
@db
def venues(db, id_venue=None, id_category=None, id_zip=None):
    q = Query(db, """
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
    q.params.update(
        id_venue=id_venue,
        id_category=id_category,
        id_zip=id_zip
    )
    print bottle.request.query.allitems()

    v = bottle.request.query.get("zip")
    if v:
        q.add("and v.zip = any(%(zip_arr)s)")
        q.params["zip_arr"] = v.split(',')
    v = bottle.request.query.get("key_category")
    if v:
        q.add("and v.key_category = any(%(key_category_arr)s)")
        q.params["key_category_arr"] = map(int, v.split(','))
    l = bottle.request.query.get("location")
    r = bottle.request.query.get("radius")
    if l and r:
        location = l.split(',')
        q.add("""
            and ST_Distance_Sphere(
                    v.loc,
                    ST_SetSRID(ST_Point(%(lng)s, %(lat)s), 4326)
                ) <= %(radius)s
        """)
        q.params.update(
            lng=float(location[0]),
            lat=float(location[1]),
            radius=float(r)
        )

    q.map['location'] = json.loads
    print q.get_sql(), q.params
    return json.dumps(
        venue_links(q(), id_venue)
    )


@app.route(ep.zips)
@app.route(ep.zip)
@db
def zips(db, id_zip=None):
    if id_zip:
        zips = [{"zip": id_zip}]
    else:
        zips = Query(db, """
            select distinct zip from venue.venue
        """)()
    return json.dumps(
        zip_links(zips, id_zip)
    )


@app.route(ep.root)
@app.route(ep.index)
def index():
    return index_links({})


### start


app.run(
    host=config.address or '0.0.0.0',
    port=config.port or '8080',
    reloader=config.reloader,
    debug=True
)