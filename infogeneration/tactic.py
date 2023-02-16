from . import AUTGEN
from rdfloader import extension_classes as extc
import programloader
from programloader import PROLOA_NS as PROLOA
from programloader import RDF_NS as RDF
import rdfloader
import rdflib
import typing as typ
import itertools as it
import queue

class rdfgraph_finder:
    """This object is used to find the input for given program.

    :cvar program: program 
    :cvar var_to_mutable: Mapping
    """
    program: object
    """Program for which this object is created"""
    var_to_mutable: dict
    """Mapping from program variables to mutable nodes, which hold the 
    information about input and output arguments of the program.
    """
    mutable_to_arg: dict[programloader.mutable_resource, programloader.arg]
    """Mapping of mutable nodes of program-arguments to their arguments
    """

    def __init__(self, program):
        self.program = program
        self.mutable_to_arg = {}
        for arg in program.app_args:
            try:
                self.mutable_to_arg[arg.example_node] = arg
            except AttributeError:
                pass
            try:
                self.mutable_to_arg[arg.generated_node] = arg
            except AttributeError:
                pass

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

    def _find_in_graph(self, rdfgraph: rdflib.Graph) -> dict[programloader.arg, rdflib.IdentifiedNode]:
        """Find programinput in given rdfgraph

        :return: Mapping of the program-arguments as object to the
            resourcenames used
        """
        arg_to_resource: dict[programloader.arg, rdflib.IdentifiedNode]
        for found_nodes in rdfgraph.query(self.queryterm):
            arg_to_resource = {}
            for var, mutable in self.var_to_mutable.items():
                arg = self.mutable_to_arg[mutable]
                arg_to_resource[arg] = found_nodes[var]
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
            axioms.extend([(app_identifier, arg.iri, arg_target),
                           (arg.iri, RDF.a, PROLOA.arg),
                           ])
        return axioms


class tactic_priority_organizer:
    graphfinder: dict[programloader.program, rdfgraph_finder]
    """Mapping of used programs their graphfinders."""
    _app_prioritiyqueue: queue.PriorityQueue[float, programloader.app]

    def execute_first_app(self, rdfgraph=None) \
            -> (str, typ.Iterable[rdflib.graph._TripleType]):
        """Returns the first app in the priorityQueue.
        If a rdfgraph is given, checks in the graph the current priorities
        and given apps. So if some other thing can execute the apps or
        because of some other reason the graph changes, this will reload
        all information.
        :raises: queue.Empty
        """
        if rdfgraph is not None:
            raise NotImplementedError("Yet no rdfgraph is supported as input")
        try:
            _, myApp = self._app_priorityqueue.get_nowait()
        except queue.Empty:
            raise
        returnstring, new_axioms = myApp()
        return returnstring, new_axioms

    def __init__(self, uses):
        self.graphfinder = {}
        for pro in uses:
            self.graphfinder[pro] = rdfgraph_finder(pro)
        self._app_priorityqueue = queue.PriorityQueue()
        self._current_used_rdfgraph = rdflib.Graph()
        self.saved_objects = {}
        for program in uses:
            self.saved_objects[program.iri] = [program]
            for arg in program.app_args:
                self.saved_objects[arg.iri] = [arg]

    def get_priorities(self, rdfgraph: rdflib.Graph) \
            -> typ.Iterable[rdflib.graph._TripleType]:
        """Generates info, which programs can be used on the given data
        and what the priority of those programs are
        """
        pro: programloader.program
        finder: rdfgraph_finder
        arg_to_resource: dict[programloader.arg, rdflib.IdentifiedNode]
        newaxioms: list[rdflib.graph._TripleType] = []
        for pro, finder in self.graphfinder.items():
            for arg_to_resource in finder._find_in_graph(rdfgraph):
                app_identifier = rdflib.BNode()
                tmp_axioms = finder.create_app(arg_to_resource, app_identifier)
                newaxioms.extend(tmp_axioms)
                tmp_prio = rdflib.Literal(self.calculate_priority())
                newaxioms.append((app_identifier, AUTGEN.priority, tmp_prio))

                tmp_graph = rdflib.Graph()
                for ax in it.chain(tmp_axioms,rdfgraph):
                    tmp_graph.add(ax)
                self.saved_objects = rdfloader.load_from_graph(\
                        programloader.input_dict, tmp_graph, \
                        wanted_resources=[app_identifier], \
                        iri_to_pythonobjects=self.saved_objects)
                try:
                    new_app = self.saved_objects[app_identifier][0]
                except Exception as err:
                    raise Exception(self.saved_objects) from err
                self._app_priorityqueue.put((tmp_prio, new_app))

        for ax in it.chain(newaxioms, rdfgraph):
            self._current_used_rdfgraph.add(ax)

        return newaxioms

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
    uses: list[programloader.program]
    """all availagle programs which are used, by this tactic"""
    def __init__(self, uri, uses: extc.info_attr_list(AUTGEN.uses)):
        self.uri = uri
        self.uses = list(uses)
        self._typecontrol_uses(self.uses)
        super().__init__(self.uses) #tactic_priority_organizer

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

