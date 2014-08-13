TP
==

Setup
-----
```sh
git clone https://github.com/kuulemart/tp.git
cd tp
bash setup.sh
```

#### PostgreSQL and Postgis
#### Python packages
* [psycopg2]
* [bottle]
* [foursquare]

```sh
pip install -r requirements.txt
```

#### Application


[postgis]:http://daringfireball.net/
[postgresql]:http://daringfireball.net/
[psycopg2]:http://daringfireball.net/
[bottle]:http://daringfireball.net/
[foursquare]:http://daringfireball.net/
[github]:http://github.com

Components
----------
#### Scraper
#### Importer
#### Server

API
---

#### /api/v1/categories/<id_category:int>
#### /api/v1/venues/<id_venue:int>/nearby
#### /api/v1/zips/<id_zip>
#### /api/v1/index
#### /api/v1/venues/<id_venue:int>
#### /api/v1/venues
#### /api/v1/categories/<id_category:int>/venues
#### /api/v1/zips/<id_zip>/venues
#### /api/v1/zips
#### /api/v1/categories

