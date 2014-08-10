#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import json
import bottle
from util import read_config, config_logging, connection_pool, AttrDict


### setup


config = read_config("api")
log = config_logging(config)
app = bottle.Bottle()
db = connection_pool(1, int(config.max_connections or 10), config.db)

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


def links(items, name, item_linker):
    return index_links({
        name: map(item_linker, items),
    })



### query builder


class Query:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.parts = AttrDict.fromkeys(["where"], [])
        self.map = {}

    def where(self, where, condition=True):
        if condition:
            self.parts.where.append(where)
        return self

    def __call__(self, *p, **kw):
        sql = self.sql
        if self.parts.where:
            sql += (' where %s' % ' and '.join(self.parts.where))
        self.db.execute(sql, p or kw)
        result = self.db.fetchall()
        map(lambda r: r.update((k, f(r[k])) for k,f in self.map.items()), result)
        return result


### routes


@app.route(url('categories'))
@app.route(url('categories/<id:int>'))
@db
def categories(db, id=None):
    q = Query(db, "select id, name from venue.category")
    q.where("id = %s", id)
    return json.dumps(links(q(id), "categories", category_links))


@app.route(url('venues'))
@app.route(url('venues/<id_venue:int>'))
@app.route(url('categories/<id_category:int>/venues'))
@app.route(url('zips/<zip>/venues'))
@db
def venues(db, id_venue=None, id_category=None, zip=None):
    sql = """
        select v.id, v.name, v.zip, v.address, v.phone, v.key_category
             , ST_AsGeoJSON(v.loc) as location
             , c.name as category
        from venue.venue v
        join venue.category c on v.key_category = c.id
    """
    q = Query(db, sql)
    q.where("v.id = %(id_venue)s", id_venue)
    q.where("c.id = %(id_category)s", id_category)
    q.where("v.zip = %(zip)s", zip)
    q.map['location'] = json.loads
    venues = q(id_venue=id_venue, id_category=id_category, zip=zip)
    return json.dumps(links(venues, "venues", venue_links))


@app.route(url('zips'))
@app.route(url('zips/<zip>'))
@db
def zips(db, zip=None):
    if zip:
        zips = [{"zip": zip}]
    else:
        zips = Query(db, "select distinct zip from venue.venue")()
    return json.dumps(links(zips, "zips", zip_links))


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