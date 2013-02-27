README
==========

Catho is a catalog utility inspired by the awesome Robert Vasicek's 
[http://www.mtg.sk/rva/](Cathy) project.

Or put in other words, it's my excuse to hack some python. Yes, yes I
promised to do it in haskell, but i don't have time now :P

Installation
----------

    cabal install

Use
----------
Add a catalog (name inferred from path)

    catho add path

Add a catalog with alias

    catho add path alias  

Remove a catalog

    catho rm path

Search for expr (filename) in all catalogs

    catho search expr

Search for expr (filename) in a specific catalog

    catho search expr catalog

List all catalogs

    catho list

Find apparently existing files from dir in the catalog

    catho scan dir

Import existing cathy catalogs to the catho format

    catho import file
    
Developing
----------

    ghc catho.hs

or

    cabal configure
    cabal build

Catalogs are automatically added to the .catho directory, and
correspond to sqlite3 databases, for more info about catalogs
see the catalog.sql file.
