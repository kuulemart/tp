#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RESTful API server
"""

import os
import json
import bottle
import bottle_pgsql
from util import read_config, config_logging

config = read_config("api")
log = config_logging(config)
app = bottle.Bottle()
plugin = bottle_pgsql.Plugin(config.db)
app.install(plugin)

def makeurl(*path, **kw):
    parts = []
    full = kw.get("full", False)
    if full:
        parts.append("%s://%s" % bottle.request.urlparts[:2])
    else:
        parts.append("/")
    parts.append("api/v1")
    parts.extend(map(str, path))
    return os.path.join(*parts)

def index_links(data):
    data.update(_links={
        "index": {"href": makeurl("index", full=True)},
        "venues": {
            "href": makeurl("venues", full=True),
            "parameters": ["zip", "key_category", "location", "radius"]
        },
        "categories": {"href": makeurl("categories", full=True)},
    })
    return data

def venue_links(data):
    data.update(_links={
        "self": {"href": makeurl("venues", data['id'], full=True)},
        "category": {"href": makeurl("categories", data['key_category'], full=True)},
    })
    return data

def category_links(data):
    data.update(_links={
        "self": {"href": makeurl("categories", data['id'], full=True)},
        "venues": {"href": makeurl("categories", data['id'], "venues", full=True)},
    })
    return data

@app.route(makeurl('categories'))
@app.route(makeurl('categories/<id:int>'))
def categories(db, id=None):
    sql = 'SELECT id, name from venue.category'
    if id:
        sql += '\nwhere id = %s'
    db.execute(sql, [id])
    categories = db.fetchall()
    data = index_links({
        "categories": map(category_links, categories),
    })
    return json.dumps(data)

@app.route(makeurl('venues'))
@app.route(makeurl('venues/<id_venue:int>'))
@app.route(makeurl('categories/<id_category:int>/venues'))
def venues(db, id_venue=None, id_category=None):
    sql = """
        SELECT v.id, v.name, v.zip, v.address, v.phone, v.key_category
             , ST_AsGeoJSON(v.loc) as location
             , c.name as category
        from venue.venue v
        join venue.category c on v.key_category = c.id
    """
    if id_venue:
        sql += '\nwhere v.id = %s'
    if id_category:
        sql += '\nwhere c.id = %s'
    db.execute(sql, [id_venue or id_category])
    venues = db.fetchall()

    for venue in venues:
        venue['location'] = json.loads(venue['location'])

    data = index_links({
        "venues": map(venue_links, venues),
    })
    return json.dumps(data)


@app.route(makeurl())
@app.route(makeurl('index'))
def index(db):
    return index_links({})

app.run(host=config.address, port=config.port, reloader=config.reloader)