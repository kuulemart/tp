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
    -- transform and upsert venue data from staging
    with
        data as (
            select $1 as source, id as source_id, key_category, name
                 --, ST_SetSRID(ST_Point(lng, lat), 4326)::geometry as loc
                 , ST_Point(lng, lat) as loc
                 , zip, address, phone
            from staging.venue
        ),
        upsert as (
            update venue.venue v
                set key_category = d.key_category
                  , name = d.name
                  , loc = d.loc
                  , zip = d.zip
                  , address = d.address
                  , phone = d.phone
            from data d
            where v.source = d.source
              and v.source_id = d.source_id
            returning v.*
        )
        insert into venue.venue
            (source, source_id, key_category, name, loc, zip, address, phone)
        select *
        from data d
        where d.source||':'||d.source_id not in (
            select source||':'||source_id from upsert
        );
$$
language sql security definer;