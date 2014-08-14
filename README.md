TP
==

Setup
-----

### Before setup

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

### Setup process

* [psycopg2]
* [bottle]
* [foursquare]

```sh
pip install -r requirements.txt
```

#### Application


Components
----------

#### Data Scrapers
Collect data from external sources and import to database

* scraper.py - contains scraper base classes and discovers and runs scrapers
* scraper_4sq_venues.py - foursquare venue scraper

#### Data Processors
Import data and perform misc data processing tasks

* import_area_data.py - imports bayarea data from file
* process_scraper_area.py - builds scraping area data from imported bay area zip polygons

#### API Server
* api.py - RESTful API server

API
---
[HAL - Hypertext Application Language][hal]

#### /api/v1/index
#### /api/v1/categories
#### /api/v1/categories/<id_category:int>
#### /api/v1/categories/<id_category:int>/venues
#### /api/v1/zips
#### /api/v1/zips/<id_zip>
#### /api/v1/zips/<id_zip>/venues
#### /api/v1/venues
#### /api/v1/venues/<id_venue:int>
#### /api/v1/venues/<id_venue:int>/nearby

[postgis]:http://daringfireball.net/
[postgresql]:http://daringfireball.net/
[psycopg2]:http://daringfireball.net/
[bottle]:http://daringfireball.net/
[foursquare]:http://daringfireball.net/
[github]:http://github.com
[hal]:http://stateless.co/hal_specification.html
[json-view]:https://chrome.google.com/webstore/detail/jsonview/chklaanhfefbnpoihckbnefhakgolnmc
[json-formatter]:https://github.com/callumlocke/json-formatter
