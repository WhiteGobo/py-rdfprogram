from . import tactic as Tactic
import itertools as it
import rdfloader
import abc
import programloader

from rdfloader import annotations as extc
from . import namespaces
import rdflib
import typing as typ
import logging
logger = logging.getLogger(__name__)
import importlib.resources
autgen_path = importlib.resources.files(namespaces).joinpath("autgen2.ttl")
from programloader import PROLOA_NS as PROLOA

from rdfloader.rdf_namespace import rdf_namespace
AUTGEN = rdf_namespace.from_file(autgen_path, namespace="http://example.com/automaticgenerator#", format="ttl")


#program_path = importlib.resources.files(test_src).joinpath( "myprogram.py" )
#program_uri = rdflib.URIRef(pathlib.Path(program_path).as_uri())
#rdf_namespace.from_file()


class information_save:
    temporary_directory: str
    def copy_generated_information(self):
        pass

class priority_project:
    #@property
    #@abc.abstractmethod
    #def inner_information_graph(self) -> rdflib.Graph:
    #    pass

    priority_reference: rdflib.URIRef
    """Used priority of this app inside the inner_information_graph"""
    def __init__(self, priority_reference=None):
        if priority_reference is None:
            self.priority_reference = rdflib.URIRef("http://example.com/bubru#priority")
        else:
            self.priority_reference = priority_reference
        #self.inner_information_graph.add((self.uri, AUTGEN.usesPriorityQueue, self.priority_reference))

    def _add_priority(self, app_id, priority) -> "rdflib.graph._TripleType":
        axiom = (app_id, self.priority_reference, rdflib.Literal(priority))
        self.inner_information_graph.add(axiom)
        return axiom

    def _find_first_app(self):
        query = """SELECT ?app WHERE {
            ?app <%s> ?priority .
            FILTER NOT EXISTS { <%s> <%s> ?app. }
        } ORDER BY ASC(?priority) limit 1""" \
                % (self.priority_reference, self.uri, AUTGEN.wasExecuted )
        #FILTER NOT EXISTS { ?app a proloa:failedApp. }
        return next(iter(self.inner_information_graph.query(query))).app

    def _label_as_executed(self, app_id):
        self.inner_information_graph.add((self.uri, AUTGEN.wasExecuted, app_id))


class program_container:
    #@property
    #@abc.abstractmethod
    #def inner_information_graph(self) -> rdflib.Graph:
    #    pass

    saved_objects: dict

    def __init__(self, used_tactic, saved_objects= dict()):
        self.used_tactic = used_tactic
        self.saved_objects = saved_objects
        for pro in self.used_tactic.uses:
            self.saved_objects[pro.iri] = [pro]
            for arg in pro.app_args:
                self.saved_objects[arg.iri] = [arg]

    def _get_app(self, app_id):
        if app_id in self.saved_objects:
            return self.saved_objects[app_id][0]
        else:
            logger.debug(f"Tried to retrieve not yet existing app {app_id}. "
                         "Generate it.")
            self.saved_objects = rdfloader.load_from_graph(\
                    programloader.input_dict, self.inner_information_graph, \
                    wanted_resources=[app_id], \
                    iri_to_pythonobjects=self.saved_objects)
            return self.saved_objects[app_id][0]


class project(information_save, priority_project, program_container):
    """Implements a tactic for a certain target
    """
    used_tactic: Tactic.tactic
    """Foundation to everything the project does. The tactic should give
    all needed algorithms and information used, so that the wanted
    information can be produced
    """
    variables: typ.List["rdflib.IdentifiedNode"]
    """All variable nodes, that we want to create.
    """
    target_information: typ.List["rdflib.graph._TripleType"]
    """All axioms that are required for the generated complex.
    """
    inner_information_graph: rdflib.Graph
    """This Graph holds all information needed and generated by this object"""

    def __init__(self, uri, used_tactic: extc.info_attr(AUTGEN.implements, inputtype=Tactic.tactic),
                 target_information: extc.info_targetresourceinfo(AUTGEN.target)):
        """

        :TODO: Make it possible to load and save all inner information in
            a rdf-format
        """
        self.uri = uri
        self.inner_information_graph = rdflib.Graph()

        priority_project.__init__(self)
        program_container.__init__(self, used_tactic)

        self.used_tactic = used_tactic
        self.variables = {subj for subj, _, _ in target_information}
        self.target_information = target_information
        #self.saved_objects = dict()
        #new_axioms = self._find_available_apps()
        #get_priorities(new_axioms)


    def update_working_information(self, \
            rdfgraph: typ.Iterable["rdflib.graph._TripleType"]):
        """Updates inner_information_graph. Adds all info from given rdfgraph
        and finds new apps and calculates their priority
        """
        axioms: list["rdflib.graph._TripleType"]
        apps: list[rdflib.IdentifiedNode]
        for ax in rdfgraph:
            self.inner_information_graph.add(ax)
        axioms, apps = self._find_available_apps(self.inner_information_graph)
        for app_id in apps:
            tmp_prio = self.used_tactic.calculate_priority()
            axioms.append(self._add_priority(app_id, tmp_prio))

        for ax in axioms:
            self.inner_information_graph.add(ax)
        return axioms, apps



    def _find_available_apps(self, infograph) \
            -> (list["rdflib.graph._TripleType"], list[rdflib.IdentifiedNode]):
        """Finds all new apps in given infograph
        """
        pro: "programloader.program"
        finder: "Tactic.rdfgraph_finder"
        arg_to_resource: dict["programloader.arg", "rdflib.IdentifiedNode"]
        new_axioms: list["rdflib.graph._TripleType"] = []
        new_apps: list[rdflib.BNode] = []
        for pro, finder in self.used_tactic.graphfinder.items():
            logger.debug(f"Search for new apps with {finder}")
            for arg_to_resource in finder._find_in_graph(infograph):
                logger.debug(f"Found possible inputs: {arg_to_resource}")
                app_identifier = rdflib.BNode()
                new_apps.append(app_identifier)
                tmp_axioms = finder.create_app(arg_to_resource, app_identifier)
                new_axioms.extend(tmp_axioms)

        return new_axioms, new_apps


    def _get_priorities(self, axioms):
        """

        :param axioms: Information about apps, from which 
        :type axioms: typ.Iterator[rdflib.graph._TripleType]
        """
        raise NotImplementedError()
        

    def get_priorities(self, infograph: "rdflib.Graph")\
            -> typ.Iterable["rdflib.graph._TripleType"]:
        """Generates info, which programs can be used on the given data
        and what the priority of those programs are

        :TODO: remove this method and automatize the things, that are done here
        """
        raise Exception()
        pro: "programloader.program"
        finder: "Tactic.rdfgraph_finder"
        arg_to_resource: dict["programloader.arg", "rdflib.IdentifiedNode"]
        newaxioms: list["rdflib.graph._TripleType"] = []
        for pro, finder in self.used_tactic.graphfinder.items():
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

        return priority_axioms

    def execute_first_app(self):
        app_id = self._find_first_app()
        self._label_as_executed(app_id)
        myapp = self._get_app(app_id)
        logger.debug(f"Executed: {myapp}")
        #print(self.inner_information_graph.serialize())
        returnstring, new_axioms = myapp()

        self.update_working_information(new_axioms)
        return returnstring, new_axioms
        

input_dict = {AUTGEN.project: project}
