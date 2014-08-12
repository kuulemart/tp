--
-- staging
--

create schema staging;

-- venue staging data

create table staging.venue
( id text not null primary key
, key_category bigint not null
, name text not null
, lat double precision not null
, lng double precision not null
, zip text not null
, address text
, phone text
);

--
-- venue
--

create schema venue;

-- venue data

create table venue.venue
( id bigserial primary key
, source text not null
, source_id text not null
, key_category bigint not null
, name text not null
, loc geometry(point, 4326) not null
, zip text not null
, address text
, phone text
);

create index venue_key_category_idx on venue.venue(key_category);
create index venue_loc_idx on venue.venue using gist(loc);
create index venue_zip_idx on venue.venue(zip);
create index venue_source_idx on venue.venue(source, source_id);

-- venue categories

create table venue.category
( id bigserial primary key
, name text not null
);


--
-- area
--

create schema area;

-- area

create table area.area
( id bigserial primary key
, area text not null
, zip text not null
, po_name  text not null
, geom geometry not null
--, geom geography not null
--, geom geometry(polygon, 4326) not null
);


--
-- scraper
--

create schema scraper;

-- category mapping to source category

create table scraper.venue_category
( id bigserial primary key
, source text not null
, key_category bigint not null
, value text not null
);

create index venue_category_source_key_category_idx on scraper.venue_category(source, key_category);

-- scraping areas

create table scraper.venue_area
( id bigserial primary key
, source text not null
, name text not null
, value text not null
);

create index venue_area_source_idx on scraper.venue_area(source);
