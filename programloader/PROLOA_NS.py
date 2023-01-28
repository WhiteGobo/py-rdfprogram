import rdflib
from rdflib import URIRef

BASE = "http://example.com/programloader/"
program = URIRef( f"{BASE}program" )
arg = URIRef( f"{BASE}arg" )
link = URIRef( f"{BASE}link" )
app = URIRef( f"{BASE}app" )
mutable_resource = URIRef( f"{BASE}mutable_resource" )

hasArgument = URIRef( f"{BASE}hasArgument")
id = URIRef( f"{BASE}id" )
describedBy = URIRef( f"{BASE}describedBy" )
executes = URIRef( f"{BASE}executes" )
