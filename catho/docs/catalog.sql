-- all catalogs are written to ~/.catho/ and are sqlite3 databases
-- each file corresponds to one sqlite3 databes with the following 
-- format:

-- METADATA table
CREATE TABLE METADATA(key TEXT, value TEXT);

-- mandatory key/values in this table for version 1
-- key                value
-- version            1
-- name               %s must be equal to filename
-- path               # original indexed path
-- createdate         # date of creation of the db
-- lastmodifdate      # date of last modification of the db

-- optional key/values (some for performance reasons)
-- lastcrc            #
-- size               #
-- numdir             # 
-- numfiles           #
-- hash type          # type of hash function included in the catalog, if it includes hashes, default=SHA-1
-- notes              # eventual notes for extra info in the catalog


-- CATALOG table
CREATE TABLE CATALOG(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, date INTEGER NOT NULL, size INTEGER NOT NULL, path TEXT NOT NULL, hash TEXT);
-- id sequential id
-- name file name
-- date includes time and is represented in unix time > (1970)
-- length file length in bytes
-- path original path
-- hash is optional for complete indexing

-- -- optional indexes, to speed queries (can double the size of the db)
-- CREATE INDEX hash_idx ON CATALOG(hash);
-- CREATE INDEX file_idx ON CATALOG(path, name);
-- DROP INDEX hash_idx;
-- DROP INDEX file_idx;

-- -- optimize DB (erase erased file space, avoid table fragmentation)
-- VACUUM;

-- -- optimize DB stats (to optimize queries)
-- ANALYZE;
