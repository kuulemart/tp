/*
    FUNCTIONS
*/

create or replace function scraper.get_venue_category
( source text
, out key_category bigint
, out value text
) returns setof record
as
$$
    select key_category, value
    from scraper.venue_category
    where source = $1;
$$
language sql security definer;


create or replace function scraper.get_venue_area
( source text
, out name text
, out value text
) returns setof record
as
$$

    select name, value
    from scraper.venue_area
    where source = $1;
$$
language sql security definer;


create or replace function staging.process_venue
( source text
) returns void
as
$$
    -- remove old records having data in staging
    delete from venue.venue
    where source = $1
      and source_id in (select id from staging.venue);

    -- transform and insert from staging
    insert into venue.venue
        (source, source_id, key_category, name, loc, zip, address, phone)
    select $1, id, key_category, name, ST_MakePoint(lat, lng), zip, address, phone
    from staging.venue;
$$
language sql security definer;