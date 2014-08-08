/*
    DATA
*/

-- clean tables

truncate table venue.category;
truncate table scraper.venue_category;
truncate table scraper.venue_area;

-- insert data

insert into venue.category(name)
    values (E'Cafe'),
           (E'Gym');

insert into scraper.venue_category(source, value, key_category)
    select E'4sq', E'["Food", "Café"]', id
    from venue.category
    where name = 'Cafe';

insert into scraper.venue_category(source, value, key_category)
    select E'4sq', E'["Shop & Service", "Gym / Fitness Center"]', id
    from venue.category
    where name = 'Gym';

insert into scraper.venue_area(source, name, value)
    values (
        E'4sq',
        E'SF Bay Area',
        E'{"ne": "38.864300,-121.208199","sw": "36.893089,-123.533684"}'
    );

