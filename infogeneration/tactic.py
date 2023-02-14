from . import AUTGEN
from rdfloader import extension_classes as extc
import programloader
from programloader import PROLOA_NS as PROLOA
from programloader import RDF_NS as RDF
import rdflib
import typing as typ
import itertools as it

class rdfgraph_finder:
    program: object
    var_to_mutable: dict

    def __init__(self, program):
        self.program = program

        #        p.generated_nodes
        #        p.new_axioms
        mutable_to_var = {x:f"x{i}" for i,x in enumerate(program.example_nodes)}
        for i, y in enumerate(program.generated_nodes):
            varname = f"y{i}"
            for x, var in mutable_to_var.items():
                if y.iri == x.iri:
                    varname = var
                    break
            mutable_to_var[y] = varname
        filter_resources = set(it.chain.from_iterable(program.old_axioms))
        self.var_to_mutable = {var: node 
                               for node, var in mutable_to_var.items()
                               if node.iri in filter_resources}
        resource_to_var = {node.iri: f"?{var}" 
                           for node, var in mutable_to_var.items()
                           if node.iri in filter_resources}
        search_axioms = [tuple(resource_to_var.get(x, f"<{x}>") for x in ax) 
                         for ax in program.old_axioms]
        self.queryterm ="""
            SELECT %s
            WHERE {%s
            }""" %(" ".join(resource_to_var.values()),
                   "\n".join(f"{s} {p} {o} ." for s,p,o in search_axioms)
                  )
        assert all(all(isinstance(x, (rdflib.URIRef, rdflib.Literal)) 
                       or x in resource_to_var 
                       for x in ax) 
                   for ax in program.old_axioms)

    def find_in_graph(self, rdfgraph: rdflib.Graph) -> dict[programloader.arg, rdflib.IdentifiedNode]:
        arg_to_resource: dict[programloader.arg, rdflib.IdentifiedNode]
        for found_nodes in rdfgraph.query(self.queryterm):
            arg_to_resource = {}
            for var, mutable in self.var_to_mutable.items():
                arg_to_resource[mutable] = found_nodes[var]
            yield arg_to_resource

    def create_app(self, arg_to_resource, app_identifier=None):
        """Create all information for an app to given input resources

        :param app_identifier: Resource id to use in axioms for the app
        :type app_identifier: rdflib.IdentifiedNode
        :param arg_to_resource:
        :type arg_to_resource: dict[programloader.arg, rdflib.IdentifiedNode]
        :return: All axioms needed for the app
        """
        if app_identifier is None:
            app_identifier = rdflib.BNode()
        axioms = [
                (app_identifier, RDF.a, PROLOA.app),
                (app_identifier, PROLOA.executes, self.program.iri),
                ]
        for arg, arg_target in arg_to_resource.items():
            axioms.append((app_identifier, arg.iri, arg_target))
        return axioms


class tactic_priority_organizer:
    graphfinder: dict[rdflib.IdentifiedNode, rdfgraph_finder]
    def __init__(self, uses):
        self.graphfinder = {}
        for p in uses:
            self.graphfinder[p.iri] = rdfgraph_finder(p)

    def get_priorities(self, rdfgraph: rdflib.Graph) \
            -> typ.Iterable[rdflib.graph._TripleType]:
        arg_to_resource: dict[programloader.arg, rdflib.IdentifiedNode]
        newaxioms = []
        for p_iri, finder in self.graphfinder.items():
            for arg_to_resource in finder.find_in_graph(rdfgraph):
                app_identifier = rdflib.BNode()
                newaxioms.extend(finder.create_app(arg_to_resource, app_identifier))
                tmp_prio = rdflib.Literal(self.calculate_priority())
                newaxioms.append((app_identifier, AUTGEN.priority, tmp_prio))
        return newaxioms

    def calculate_priority(self):
        return 0.0



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

