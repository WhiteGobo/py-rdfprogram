import rdflib
from rdflib import URIRef

BASE = URIRef("http://example.com/automaticgenerator#")
"""Baselink. Use as prefix"""
tactic = URIRef( f"{BASE}tactic" )
"""Class for all tactics"""

uses = URIRef( f"{BASE}uses")
"""Targeted proloa:program by this property is used by tactic"""

priority = URIRef(f"{BASE}priority")
