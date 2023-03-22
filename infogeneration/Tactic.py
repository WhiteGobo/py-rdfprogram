from . import AUTGEN
from rdfloader import annotations as extc
import programloader
from programloader import PROLOA_NS as PROLOA
from programloader import RDF_NS as RDF
import rdfloader
import rdflib
import typing as typ
import itertools as it
import queue
import pyparsing.exceptions
from . import abstractclasses as myabc


class program_container:
    uses: list[myabc.program]
    """all availagle programs which are used, by this tactic"""
    def __init__(self, uses, **kwargs):
        super().__init__(**kwargs)
        self.uses = list(uses)
        try:
            [myabc.type_control(myabc.program, p) for p in uses]
        except TypeError as err:
            raise TypeError(f"input uses for {type(self)}", uses )


class tactic_priority_organizer(program_container):
    def calculate_priority(self):
        """Estimates the priority. This method isnt ready yet
        """
        return 0.0



class tactic(tactic_priority_organizer):
    """To generate a certain output with given programs, this class
    is used. It looks up all available input-constellation for the given 
    programs and estimates, which program-usage should be used via 
    a priority queue. It also organizes the usage of the programs.
    """
    def __init__(self, uri, uses: extc.info_attr_list(AUTGEN.uses)):
        super().__init__(uses=uses) #tactic_priority_organizer
        self.uri = uri
