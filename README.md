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

    # Prepare catalog folder
    catho init

    # Add a catalog with alias
    catho add name path  

    # Remove a catalog
    catho rm name

    # Search for expr (filename) in all catalogs
    catho search expr

    # Search for expr (filename) in a specific catalog
    catho search name expr

    # List all catalogs
    catho ls

    # Find apparently existing files from dir in the catalog
    catho scan name dir

    # Import existing cathy catalogs to the catho format
    catho import file.cat
    
Developing
----------

The catalog correspond to a simple sqlite3 database, for more info
about the catalog structure, see the docs/catalog.sql file. Catalogs
are saved automatically in the ~/.catho folder.

We would like to create a sort of simple minimalist catalog system so
people can create nicer tools based on the catho system (e.g. GUI,
web, etc).

Collaboration
----------
If you want to add some functionality or change something please
execute the testcases to be sure everything is working, and/or modify
them if necessary so they don't break.

Another common sense rule is don't add code that would be eventually
used, to keep maintenance easy, please only add code that is related
to some existing and tested funtionality.
