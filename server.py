#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import json
import bottle
import util


### setup


config = util.read_config("api")
log = util.config_logging(config).getLogger("server")
app = bottle.Bottle()
db = util.connection_pool(1, int(config.max_connections or 10), config.db)

def url(*path, **kw):
    parts = []
    full = kw.get("full", False)
    version = kw.get("version", "v1")
    if full:
        parts.append("%s://%s" % bottle.request.urlparts[:2])
    else:
        parts.append("/")
    parts.append("api")
    parts.append(version)
    parts.extend(map(str, path))
    return os.path.join(*parts)


### hypermedia helpers


def href(url, **kw):
    return dict(kw, href=url)

def index_links(data):
    data.update(_links={
        "self": href(bottle.request.url),
        "index": href(url("index", full=True)),
        "venues": href(
            url("venues", full=True),
            parameters=["zip", "key_category", "location", "radius"]
        ),
        "categories": href(url("categories", full=True)),
        "zips": href(url("zips", full=True)),
    })
    return data

def venue_links(data):
    data.update(_links={
        "self": href(url("venues", data['id'], full=True)),
        "category": href(url("categories", data['key_category'], full=True)),
        "zip": href(url("zips", data['zip'], full=True)),
    })
    return data

def category_links(data):
    data.update(_links={
        "self": href(url("categories", data['id'], full=True)),
        "venues": href(url("categories", data['id'], "venues", full=True)),
    })
    return data

def zip_links(data):
    data.update(_links={
        "self": href(url("zips", data['zip'], full=True)),
        "venues": href(url("zips", data['zip'], "venues", full=True)),
    })
    return data


def links(name, items, item_linker):
    return index_links({
        name: map(item_linker, items),
    })



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


@app.route(url('categories'))
@app.route(url('categories/<id:int>'))
@db
def categories(db, id=None):
    q = Query(db, """
        select id, name
        from venue.category
        where 1 = 1
    """)
    q.add("and id = %s", id)
    return json.dumps(links("categories", q(id), category_links))


@app.route(url('venues'))
@app.route(url('venues/<id_venue:int>'))
@app.route(url('categories/<id_category:int>/venues'))
@app.route(url('zips/<zip>/venues'))
@db
def venues(db, id_venue=None, id_category=None, zip=None):
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
    q.add("and v.zip = %(zip)s", zip)
    q.params.update(
        id_venue=id_venue,
        id_category=id_category,
        zip=zip
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
    return json.dumps(links("venues", q(), venue_links))


@app.route(url('zips'))
@app.route(url('zips/<zip>'))
@db
def zips(db, zip=None):
    if zip:
        zips = [{"zip": zip}]
    else:
        zips = Query(db, """
            select distinct zip from venue.venue
        """)()
    return json.dumps(links("zips", zips, zip_links))


@app.route(url())
@app.route(url('index'))
def index():
    return index_links({})


### start


app.run(
    host=config.address or '0.0.0.0',
    port=config.port or '8080',
    reloader=config.reloader
)