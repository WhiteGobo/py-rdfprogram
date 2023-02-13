from . import AUTGEN
from rdfloader import extension_classes as extc
import programloader
import rdflib
import typing as typ

class rdfgraph_finder:
    def __init__(self, program):
        self.program = program
        self.queryterm ="""
            SELECT ?x
            WHERE {?x ?x ?x}
            """

    def find_in_graph(self, rdfgraph: rdflib.Graph):
        for found_nodes in rdfgraph.query(self.queryterm):
            yield {x: y for x, y in zip(origin, found_nodes)}


class tactic_priority_organizer:
    graphfinder: dict[rdflib.IdentifiedNode, rdfgraph_finder]
    def __init__(self, uses):
        self.graphfinder = {}
        for p in uses:
            self.graphfinder[p.iri] = rdfgraph_finder(p)

    def get_priorities(self, rdfgraph: rdflib.Graph) \
            -> typ.Iterable[rdflib.graph._TripleType]:
        newaxioms = []
        for p_iri, finder in self.graphfinder.items():
            for nodes in finder.find_in_graph(rdfgraph):
                raise Exception(nodes)
        return newaxioms


class tactic(tactic_priority_organizer):
    uses: programloader.program
    """all availagle programs which are used, by this tactic"""
    def __init__(self, uri, uses: extc.info_attr_list(AUTGEN.uses)):
        self.uri = uri
        self._typecontrol_uses(uses)
        self.uses = uses
        super().__init__(uses) #tactic_priority_organizer

    @classmethod
    def _typecontrol_uses(cls, uses: list[programloader.program]):
        for p in uses:
            try:
                p.example_nodes
                p.generated_nodes
                p.old_axioms
                p.new_axioms
            except AttributeError as err:
                raise TypeError("must all be programloader.program") from err



