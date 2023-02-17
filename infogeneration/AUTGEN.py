import rdflib
from rdflib import URIRef

BASE = URIRef("http://example.com/automaticgenerator#")
"""Baselink. Use as prefix"""
tactic = URIRef( f"{BASE}tactic" )
"""Class for all tactics"""

uses = URIRef( f"{BASE}uses")
"""Targeted proloa:program by this property is used by tactic"""

priority = URIRef(f"{BASE}priority")

priorityQueue = URIRef(f"{BASE}priorityQueue")
"""Propertyclass of priority queues of a tactic. Specifies in which order
apps should be executed.
"""
usesPriorityQueue = URIRef(f"{BASE}usesPriorityQueue")
"""Connects a tactic to its priorityQueue."""
