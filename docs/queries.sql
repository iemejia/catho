-- some interesting queries

-- find duplicates
SELECT hash, path || name FROM catalog WHERE hash NOT IN (SELECT hash FROM catalog GROUP BY hash HAVING ( COUNT(hash) = 1 )) order by hash;

-- get the 10 biggest files
SELECT * FROM catalog ORDER BY size DESC LIMIT 10;

-- get the 10 more recent files
SELECT * FROM catalog ORDER BY date DESC LIMIT 10;

-- get date in a nicer format
SELECT datetime(date, 'unixepoch') FROM catalog ORDER BY date DESC LIMIT 10;

-- count duplicates per file
SELECT count(hash), name FROM catalog GROUP BY hash HAVING (COUNT(hash) > 1);

-- 20 biggest repeated files
SELECT count(hash), name, size FROM catalog GROUP BY hash HAVING (COUNT(hash) > 1) ORDER BY size DESC LIMIT 20;
or
SELECT size, path || name, datetime(date, 'unixepoch') FROM catalog WHERE hash NOT IN (SELECT hash FROM catalog GROUP BY hash HAVING ( COUNT(hash) = 1 )) ORDER BY size DESC, hash LIMIT 20;

-- total size per filetype (e.g. mp3)
SELECT sum(size) FROM catalog WHERE name LIKE '%.mp3';

-- most repeated file by name (curious, usually is index.html)
SELECT max(num_names), name FROM (SELECT count(name) as num_names, name FROM catalog GROUP BY name having(COUNT(name) > 1));
