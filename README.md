Folder content
===============

* /python - folder containing python code
    * util.py - utilities and helpers library
    * scraper.py - scraper base classes and srapers runner
    * scraper_4sq_venues.py - foursquare venues scraper
    * api.py - api server
    * bottle_pgpool.py - psycopg2 pooler plugin for bottle
    * pipeline.py - processing pipeline microframework. used for creating data pipelines
    * import_area_data.py - bayareadata importer
    * process_scraper_area.py - scraper area data generator
* /sql - folder containing database scripts and data
    * database.sql - database creation
    * tables.sql - table structures
    * data.sql - initial data
    * functions.sql - database functions
* /. - root folder contains help, import data and bash scripts for setup and running
    * README.md - this document
    * bayareadata.gz - bay area zip area polygons
    * install.sh - package install script
    * setup.sh - application setup
    * run_scraper.sh - starts scrapers
    * run_api_server.sh - starts api server
    * config.ini - configuration file. Contains sections for all components


Setup and usage
===============

Before setup
------------

Setup expect some components to be installed in your machine

#### PostgreSQL and Postgis
Postgresql and postgis are expected to be installed and running and your local
user should have superuser rights. If not, run:

```sh
sudo apt-get install -y postgresql postgresql-contrib postgis postgresql-9.3-postgis-2.1
sudo su - postgres
createuser <your system user name> -s
<CTRL-D>
```

#### Python packages
Python (2.7) and pip is expected to be present in system. If not, run:
```sh
sudo apt-get install -y python-pip
```

Optional virtualenv setup
```sh
sudo apt-get install -y python-virtualenv virtualenvwrapper
source /etc/bash_completion.d/virtualenvwrapper
mkvirtualenv tp
```

Install packages
----------------
All application python packages can be installed with single command:

```sh
./install.sh
```

Script installs following packages:

* [psycopg2] - postgresql access library
* [bottle] - simple web framework
* [foursquare] - [recommended][foursquare-libraries] foursquare api client

Packages are described in pip requirements file and can be installed manually by running:

```sh
pip install -r requirements.txt
```

pip needs additional packages libpq-dev and python-dev to build [psycopg2]


Setup database
--------------
Database setup can be performed with single command:

```sh
./setup.sh
```

Script executes database scripts from sql folder, imports bayareadata and builds scraper area data using bayareadata

Run scraper
-----------
For foursquare venue data scraping, run:

```sh
./run_scraper.sh
```

Run API server
--------------
After venue data is loaded, run api server:

```sh
./run_api_server.sh
```

Now point your browser to:

```
http://<hostname>:8080/api/v1/index
```

For best viewing experience in browser, json formatter plugin sucn as [json-view] or [json-formatter] is recommended


Components
==========

Data Processors
---------------
Import data and perform misc data processing tasks

* import_area_data.py - imports bayarea data from file
* process_scraper_area.py - builds scraping area data from imported bay area zip polygons

Processor components use pipeline library for simple and reusable workflow

Scrapers
-------------
Collect data from external sources and import to database

* scraper.py - contains scraper base classes and discovers and runs scrapers
* scraper_4sq_venues.py - foursquare venue scraper

Foursquare venue scraper uses python [foursquare] library for foursquare API access.

API Server
----------
RESTful API server

* api.py - RESTful API server

Uses python [bottle] library. Only json content-type is currently supported.


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

Respose is returned as json data. Response format follows [HAL - Hypertext Application Language][hal] representation.
Main differences is fully qualified url-s as links.

### Index
Each response has index block, containing references to endpoints.

Attributes:
* ** _links **
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
* ** _links **
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
* ** _links **
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
* ** _links **
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

[postgis]:http://www.postgis.org/
[postgresql]:http://www.postgresql.org/
[psycopg2]:http://initd.org/psycopg
[bottle]:https://github.com/defnull/bottle
[foursquare]:https://github.com/mLewisLogic/foursquare
[github]:http://github.com
[hal]:http://stateless.co/hal_specification.html
[json-view]:https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc
[json-formatter]:https://github.com/callumlocke/json-formatter
[foursquare-libraries]:https://developer.foursquare.com/resources/libraries