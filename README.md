README
==========

Catho is a catalog utility inspired by the awesome Robert Vasicek's
[http://www.mtg.sk/rva/](Cathy) project. The idea is to have an util
to save the catalog of the different files that you have in different
media, volumes, network places, etc, that you can search, and update
locally without having to put or connect to such media.

Or put in other words, it's my excuse to hack some python. Yes, yes I
promised to do it in haskell, but i don't have time now :P.

Installation
----------

TODO


Use
----------
Add a catalog with alias

    catho add name path  

Remove a catalog

    catho rm name

Search for expr (filename) in all catalogs

    catho search expr

Search for expr (filename) in a specific catalog

    catho search name expr

List all catalogs

    catho ls

Find apparently existing files from dir in the catalog

    catho scan name dir

Import existing cathy catalogs to the catho format

    catho import file.cat
    
Developing
----------

The catalog correspond to a simple sqlite3 database, for more info
about the catalog structure, see the catalog.sql file. If not defined
explicitly catalogs will be saved in the ~/.catho folder.
