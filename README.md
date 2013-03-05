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

Requirements
------------

Python version < 2.7
pip install argparse

Use
----------

    # Prepare catalog folder
    catho init

    # Add a catalog with alias
    catho add name path  

    # Remove a catalog
    catho rm name

    # Search for filenames matching with a pattern (ex. *.zip, c*.*)
      in some catalogs or in all if none is provided

    catho find pattern [catalog1] [catalog2] [catalogn]

    # List all catalogs
    catho ls

    # Find apparently existing files from dir in the catalog
    catho scan name dir

    # Import existing cathy catalogs to the catho format
    catho import file.cat
    
Developing
----------

The catalog correspond to a simple sqlite3 database, for more info
about the catalog structure, see the [docs/catalog.sql](https://github.com/iemejia/catho/blob/master/docs/catalog.sql) file. Catalogs
are saved automatically in the ~/.catho folder.

We would like to create a sort of simple minimalist catalog system so
people can create nicer tools based on the catho system (e.g. GUI,
web, etc).

Collaboration
----------
Contributions are welcome, but please add new unit tests to test your changes
and/or features.  Also, please try to make changes platform independent and
backward compatible.
