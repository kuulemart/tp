\set ON_ERROR_STOP

\set database tp

drop database if exists :database;

create database :database with encoding 'utf-8';

\connect :database

create extension postgis;

\i tables.sql
\i data.sql
\i functions.sql

-- grant rights to scraper user
\set user scraper
drop user if exists :user;
create user :user with password 'salakala';

grant connect on database :database to :user;
grant usage on schema staging to :user;
grant all on all tables in schema staging to :user;
grant execute on all functions in schema staging to :user;
grant usage on schema scraper to :user;
grant execute on all functions in schema scraper to :user;

-- grant rights to api user
\set user api
drop user if exists :user;
create user :user with password 'salakala';

grant connect on database :database to :user;
grant usage on schema venue to :user;
grant select on all tables in schema venue to :user;
