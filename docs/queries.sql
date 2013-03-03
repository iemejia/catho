-- some interesting queries

-- find duplicates
SELECT hash, path || name FROM catalog WHERE hash NOT IN (SELECT hash FROM catalog GROUP BY hash HAVING ( COUNT(hash) = 1 )) order by hash;

-- get the 10 biggest files
SELECT * FROM catalog ORDER BY size DESC LIMIT 10;

-- get the 10 more recent files
SELECT * FROM catalog ORDER BY date DESC LIMIT 10;

-- get date in a nicer format
SELECT datetime(date, 'unixepoch') FROM catalog ORDER BY date DESC LIMIT 10;
