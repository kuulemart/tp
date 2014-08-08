create schema if not exists staging;

drop table if exists staging.venue;

create table staging.venue
( id text not null primary key
, category text not null
, name text not null
, lat double precision not null
, lng double precision not null
, zip text not null
, address text
, phone text
);

create schema if not exists venue;

drop table if exists venue.venue;

create table venue.venue
( id bigserial primary key
, source text not null
, source_id text not null
, category_key bigint not null
, name text not null
, loc geometry not null
, zip text not null
, address text
, phone text
);

drop table if exists venue.category;

create table venue.category
( id bigserial primary key
, name text not null
);

create schema if not exists scraper;

drop table if exists scraper.venue_category;

create table scraper.venue_category
( id bigserial primary key
, source text not null
, key_category bigint not null
, value text not null
);

drop table if exists scraper.venue_area

create table scraper.venue_area
( id bigserial primary key
, source text not null
, name text not null
, value text not null
);

/*
	FUNCTIONS
*/

create or replace function scraper.get_venue_category
( source text
, out key_category bigint
, out value text
) returns setof record
$$
	select key_category, value
	from scraper.category
	where source = $1;
$$
language sql security definer;


create or replace function scraper.get_venue_area
( source text
, out name text
, out value text
) returns setof record
$$
	select name, value
	from scraper.area
	where source = $1;
$$
language sql security definer;


create or replace function staging.process_venue
( source text
) returns void as
$$
$$
language sql security definer;