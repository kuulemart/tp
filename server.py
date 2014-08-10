#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import json
import bottle
#import bottle_pgsql
from util import read_config, config_logging, connection_pool


### setup


config = read_config("api")
log = config_logging(config)
app = bottle.Bottle()
#plugin = bottle_pgsql.Plugin(config.db)
#app.install(plugin)
db = connection_pool(1, int(config.get("max_connections", "10")), config.db)

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
    def __init__(self, sql):
        self._sql = sql
        self._where = []
        self.map = {}

    def where(self, where, condition=True):
        if condition:
            self._where.append(where)
        return self

    def __call__(self, db, *params):
        sql = self._sql
        if self.where:
            sql += (' where %s' % ' and '.join(self.where))
        db.execute(sql, params)
        result = db.fetchall()
        map(lambda r: r.update((k, f(r[k])) for k,f in self.map.items()), result)
        return result


### routes


@app.route(url('categories'))
@app.route(url('categories/<id:int>'))
@db
def categories(db, id=None):
    q = Query("select id, name from venue.category")
    q.where("id = %s", id)
    return json.dumps(links(q(db, id), "categories", category_links))


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
    q = Query(sql)
    q.where("v.id = %s", id_venue)
    q.where("c.id = %s", id_category)
    q.where("v.zip = %s", zip)
    q.map['location'] = json.loads
    venues = q(db, id_venue or id_category or zip)
    return json.dumps(links(venues, "venues", venue_links))


@app.route(url('zips'))
@app.route(url('zips/<zip>'))
@db
def zips(db, zip=None):
    if zip:
        zips = [{"zip": zip}]
    else:
        zips = Query("select distinct zip from venue.venue")(db)
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