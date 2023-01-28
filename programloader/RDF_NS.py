import rdflib
from rdflib import URIRef

_BASE = URIRef( "http://www.w3.org/1999/02/22-rdf-syntax-ns#" )
a = URIRef( f"{_BASE}type" )
subPropertyOf = URIRef( f"{_BASE}subPropertyOf" )
