README
==========

Catho is a catalog utility inspired by the awesome Robert Vasicek's 
[http://www.mtg.sk/rva/](Cathy) project.

Or put in other words, it's my excuse to hack some haskell.

Installation
----------

    cabal install

Use
----------

    catho add path
    catho add path alias
    catho rm path
    catho search expr    
    catho search expr alias
    
Developing
----------

    ghc catho.hs

or

    cabal configure
    cabal build

