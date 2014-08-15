Overview
========
The aim of this project is to design and create database for venue data, build 
venue scrapers and expose data through RESTful API interface.


Host platform
-------------
All componets are built and tested on Ubuntu Server 14.04


Database
--------
PostgresSQL 9.3.5 with Postgis 2.1 extension is used. Database contains tables
for holding venue data, staging tables for data import and scraper configurations.

Database functions are used to provide simple API interface for scrapers. Scraper,
api and importers have all different accounts with different access rights in
database.


Data Processors
---------------
Import data and perform misc data processing tasks

* import_area_data.py - imports bayarea data from file
* process_scraper_area.py - builds scraping area data from imported bay area zip polygons

Processors use custom pipeline library for simple and reusable workflow logic.


Scrapers
-------------
Scrapers collect data from external sources and import to database. Scrapers have
base classes for reuseable and extendable logic. scraper.py has logic to discover
and execute implemented scrapers. To be discovered, all scraper implementations
should have scraper_* prefix in file, Scraper* prefix in class name and run method

* scraper.py - contains scraper base classes and discovers and runs scrapers
* scraper_4sq_venues.py - foursquare venue scraper

Foursquare venue scraper uses [recommended][foursquare-libraries] [python-foursquare]
library for foursquare API access.


API Server
----------
RESTful API server

* api.py - RESTful API server

Uses fast and simple [python-bottle] web framework. Only json content-type results 
are currently supported.



Setup and usage
===============

Folder content
--------------

* /python - folder containing python code
    * util.py - utilities and helpers library
    * scraper.py - scraper base classes and srapers runner
    * scraper_4sq_venues.py - foursquare venues scraper
    * api.py - api server
    * bottle_pgpool.py - psycopg2 pooler plugin for bottle
    * pipeline.py - processing pipeline microframework. used for creating data pipelines
    * import_area_data.py - bayareadata importer
    * process_scraper_area.py - scraper area data generator
    * crawler.py - simple api link crawler for testing
* /sql - folder containing database scripts and data
    * database.sql - database creation
    * tables.sql - table structures
    * data.sql - initial data
    * functions.sql - database functions
* /. - root folder contains help, import data and bash scripts for setup and running
    * README.md - this document
    * bayareadata.gz - bay area zip area polygons
    * install_packages.sh - package install script
    * setup.sh - application setup
    * run_scraper.sh - starts scrapers
    * run_api_server.sh - starts api server
    * config.ini - configuration file. Contains sections for all components


Before setup
------------
Setup expect some components to be installed in your machine

#### PostgreSQL and Postgis
Postgresql and postgis are expected to be installed and running and your local
user should have superuser rights. If not, run: Scraper,
api and importers have all different accounts with different access rights in
database.

```sh
sudo apt-get install -y postgresql postgresql-contrib postgis postgresql-9.3-postgis-2.1
sudo su - postgres
createuser <your system user name> -s
<CTRL-D>
```

#### Python packages
Python (2.7) and pip is expected to be present in system. To install pip, run:
```sh
sudo apt-get install -y python-pip
```

Optionally virtualenv can be installed:
```sh
sudo apt-get install -y python-virtualenv virtualenvwrapper
source /etc/bash_completion.d/virtualenvwrapper
mkvirtualenv tp
```

Packages installation
---------------------
All application python packages can be installed with single command:

```sh
./install_packages.sh
```

Script installs following packages:

* [psycopg2] - postgresql access library
* [python-bottle] - web framework
* [python-foursquare] - foursquare api client

Installable packages are described in pip requirements file and can be installed manually by running:

```sh
pip install -r requirements.txt
```

pip needs additional packages libpq-dev and python-dev to build [psycopg2]:

```sh
sudo apt-get install -y libpq-dev python-dev
```


Database setup
--------------
Database setup can be performed with single command:

```sh
./setup.sh
```

Script executes database scripts from sql folder, imports bayareadata and builds 
scraper area data using bayareadata


Run scraper
-----------
For foursquare venue data scraping, run:

```sh
./run_scraper.sh
```

Script executes scrapers runner scraper.py.


Run API server
--------------
After venue data is loaded, run api server:

```sh
./run_api_server.sh
```

Script executes api.py, the RESTful API server.


Usage
-----
API starting point is url:

```
http://<hostname>:8080/api/v1/index
```

For commandline, use curl:
```sh
curl http://<hostname>:8080/api/v1/index
```

For best viewing experience use browser with json formatter plugin such as 
[json-view] or [json-formatter]



API
===

Endpoints
---------
All parameters are optional, unless otherwise indicated.
Default limit=100 applies to all set returning endpoints. Default limit can be set in config.

### GET /api/v1/index
Links to endpoints

### GET /api/v1/categories
Venue categories

Parameters:
* **limit** - max number of items to return. default is 100 and can be set in config

### GET /api/v1/categories/<id:int>
Venue category by id

### GET /api/v1/categories/<id:int>/venues
Venues having specified category id

Parameters:
* **zip** - zip codes. Accepts multiple values, separaded by comma
* **location** - location point in longitude,latitude order. Requres radius parameter
* **radius** - radius in meters from point to search venues. Requires location parameter
* **limit** - max number of items to return

### GET /api/v1/zips
Venue zip codes

Parameters:
* **limit** - max number of items to return

### GET /api/v1/zips/<zip>
Zip by code

### GET /api/v1/zips/<zip>/venues
Venues having specified zip code

Parameters:
* **key_category** - venue category id-s. Accepts multiple values, separaded by comma
* **location** - location point in longitude,latitude order. Requres radius parameter
* **radius** - radius in meters from point to search venues. Requires location parameter
* **limit** - max number of items to return. default is 100 and can be set in config

### GET /api/v1/venues
Venues

Parameters:
* **zip** - zip codes. Accepts multiple values, separaded by comma
* **key_category** - venue category id-s. Accepts multiple values, separaded by comma
* **location** - location point in longitude,latitude order. Requres radius parameter
* **radius** - radius in meters from point to search venues. Requires location parameter
* **limit** - max number of items to return

### GET /api/v1/venues/<id:int>
Venue by id

### GET /api/v1/venues/<id:int>/nearby
Venues near to venue specified by id

Parameters:
* **zip** - zip codes. Accepts multiple values, separaded by comma
* **key_category** - venue category id-s. Accepts multiple values, separaded by comma
* **radius** - radius in meters from specified venue
* **limit** - max number of items to return


Response
--------
Respose is returned as json data with hypermedia links to related data.
Response format is inspired by [HAL - Hypertext Application Language][hal]
representation. Main differences from HAL spec is fully qualified url-s.

### Index
Each response has index block, containing references to endpoints.

Attributes:
* **_links**
   * **self** - current endpoint
   * **index** - index
   * **venues** - venues
   * **categories** - categories
   * **zips** - zip codes

Example:

```json
{ "categories" : { "href" : "http://vm:8080/api/v1/categories",
      "params" : [ "limit" ]
    },
  "index" : { "href" : "http://vm:8080/api/v1/index" },
  "self" : { "href" : "http://vm:8080/api/v1/index" },
  "venues" : { "href" : "http://vm:8080/api/v1/venues",
      "params" : [ "zip", "key_category", "location", "radius", "limit" ]
    },
  "zips" : { "href" : "http://vm:8080/api/v1/zips",
      "params" : [ "limit" ]
    }
}
```

### Venue
Venue data

Attributes:
* **_links**
   * **index links**
   * **category** - venue category
   * **zip** - venue zip
   * **nearby** - nearby venues
*  **id** - venue id
* **name** - venue name
* **zip** - venue zip code
* **address** - venue address
* **phone** - venue phone
* **key_category** - venue category id
* **category** - venue category name
* **location** - venue location
    * **lat** - latitude
    * **lng** - longitude
    * **point** - longitude,latitude

Example:
```json
{ "_links" : { "categories" : { "href" : "http://vm:8080/api/v1/categories",
          "params" : [ "limit" ]
        },
      "category" : { "href" : "http://vm:8080/api/v1/categories/1" },
      "index" : { "href" : "http://vm:8080/api/v1/index" },
      "nearby" : { "href" : "http://vm:8080/api/v1/venues/2805/nearby",
          "params" : [ "zip", "key_category", "radius", "limit" ]
        },
      "self" : { "href" : "http://vm:8080/api/v1/venues/2805" },
      "venues" : { "href" : "http://vm:8080/api/v1/venues",
          "params" : [ "zip", "key_category", "location", "radius", "limit" ]
        },
      "zip" : { "href" : "http://vm:8080/api/v1/zips/94587" },
      "zips" : { "href" : "http://vm:8080/api/v1/zips",
          "params" : [ "limit" ]
        }
    },
  "address" : "1761 Decoto Rd Union City, CA 94587 United States",
  "category" : "Cafe",
  "id" : 2805,
  "key_category" : 1,
  "location" : { "lat" : "37.58948",
      "lng" : "-122.022466",
      "point" : "-122.022466,37.58948"
    },
  "name" : "E-Bubble",
  "phone" : null,
  "zip" : "94587"
}
```

### Category
Category data

Attributes:
* **_links**
   * **index links**
   * **category_venues** - venues in current categoy
*  **id** - category id
* **name** - category name

Example:

```json
{ "_links" : { "categories" : { "href" : "http://vm:8080/api/v1/categories",
          "params" : [ "limit" ]
        },
      "category_venues" : { "href" : "http://vm:8080/api/v1/categories/1/venues",
          "params" : [ "zip", "location", "radius", "limit" ]
        },
      "index" : { "href" : "http://vm:8080/api/v1/index" },
      "self" : { "href" : "http://vm:8080/api/v1/categories/1" },
      "venues" : { "href" : "http://vm:8080/api/v1/venues",
          "params" : [ "zip", "key_category", "location", "radius", "limit" ]
        },
      "zips" : { "href" : "http://vm:8080/api/v1/zips",
          "params" : [ "limit" ]
        }
    },
  "id" : 1,
  "name" : "Cafe"
}
```

### Zip
Zip code data

Attributes:
* **_links**
   * **index links**
   * **zip_venues** - venues having current zip code
*  **zip** - zip code

Example:

```json
{ "_links" : { "categories" : { "href" : "http://vm:8080/api/v1/categories",
          "params" : [ "limit" ]
        },
      "index" : { "href" : "http://vm:8080/api/v1/index" },
      "self" : { "href" : "http://vm:8080/api/v1/zips/94301" },
      "venues" : { "href" : "http://vm:8080/api/v1/venues",
          "params" : [ "zip", "key_category", "location", "radius", "limit" ]
        },
      "zip_venues" : { "href" : "http://vm:8080/api/v1/zips/94301/venues",
          "params" : [ "key_category", "location", "radius", "limit" ]
        },
      "zips" : { "href" : "http://vm:8080/api/v1/zips",
          "params" : [ "limit" ]
        }
    },
  "zip" : "94301"
}
```


Issues
======
Issues and problems faced during design and implementation:

* environment setup - I had older and unsupported ubuntu version with broken packages. Had to
install new version first
* gis world was unfamiliar - all about spatial data, types, functions etc. lat/lng vs lng/lat
srid-s, geometry vs geography.
* foursquare api - getting access to api, max 50 results limit

TODO
====
For the future:

* Automated unit and regression tests. Currently only tests implemented are simple
crawler that validates api links and some doctests.
* Better exception handling for scraper and api - api input validation and improved
result code logic. More robust scrapers, so data errors won't break whole scraping process
* Doc improvements - documents could always be improved
* Source code comments and docs


[postgis]:http://www.postgis.org/
[postgresql]:http://www.postgresql.org/
[psycopg2]:http://initd.org/psycopg
[python-foursquare]:https://github.com/mLewisLogic/foursquare
[python-bottle]:http://github.com/defnull/bottle
[github]:http://github.com
[hal]:http://stateless.co/hal_specification.html
[json-view]:https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc
[json-formatter]:https://github.com/callumlocke/json-formatter
[foursquare-libraries]:https://developer.foursquare.com/resources/libraries