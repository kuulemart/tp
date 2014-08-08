\set ON_ERROR_STOP

\set user scraper
\set database tp

drop database if exists :database;
drop user if exists :user;

create database :database with encoding 'utf-8';
create user :user with password 'salakala';

\connect :database

create extension postgis;

\i tables.sql
\i data.sql
\i functions.sql

-- grant rights to scraper user

grant connect on database :database to :user;
grant usage on schema staging to :user;
grant all on all tables in schema staging to :user;
grant execute on all functions in schema staging to :user;
grant usage on schema scraper to :user;
grant execute on all functions in schema scraper to :user;
