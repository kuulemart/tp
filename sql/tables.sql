/*
    TABLES
*/

create schema staging;

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

create schema venue;

create table venue.venue
( id bigserial primary key
, source text not null
, source_id text not null
, key_category bigint not null
, name text not null
, loc geometry not null
, zip text not null
, address text
, phone text
);

create table venue.category
( id bigserial primary key
, name text not null
);

create schema scraper;

create table scraper.venue_category
( id bigserial primary key
, source text not null
, key_category bigint not null
, value text not null
);

create table scraper.venue_area
( id bigserial primary key
, source text not null
, name text not null
, value text not null
);
