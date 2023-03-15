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

class rdfgraph_finder:
    """This object is used to find the input for given program.

    :cvar program: program 
    :cvar var_to_mutable: Mapping
    """
    program: myabc.program
    """Program for which this object is created"""
    var_to_mutable: dict
    """Mapping from program variables to mutable nodes, which hold the 
    information about input and output arguments of the program.
    """
    mutable_to_arg: dict[myabc.mutable_resource, myabc.arg]
    """Mapping of mutable nodes of program-arguments to their arguments
    """

    bnode_queryterm: str
    """String used for query request to find possible programinputs"""
    uri_queryterm: str
    """String used for query request to find possible programinputs"""
    def __str__(self):
        typename = type(self).__name__
        return f"<{typename}:program={self.program}>"

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
        #not needed because only already existing nodes are searched for
        #for i, y in enumerate(program.generated_nodes):
        #    varname = f"y{i}"
        #    for x, var in mutable_to_var.items():
        #        if y == x:
        #            varname = var
        #            break
        #    mutable_to_var[y] = varname
        filter_resources = set(it.chain.from_iterable(program.old_axioms))
        #This seems fishy. Vartomutable shouldnt be possible
        self.var_to_mutable = {var: node 
                               for node, var in mutable_to_var.items()
                               if node in filter_resources}
        mut_to_arg = {arg.example_node: rdflib.Literal(arg.id) 
                      for arg in program.app_args 
                      if hasattr(arg, "example_node")}
        mut_to_arg.update({arg.generated_node: rdflib.Literal(arg.id)
                           for arg in program.app_args 
                           if hasattr(arg, "generated_node")})
        mut_to_arguri = {}
        for arg in program.app_args:
            if isinstance(arg.iri, rdflib.URIRef):
                if hasattr(arg, "example_node"):
                    mut_to_arguri[arg.example_node] = arg.iri
                if hasattr(arg, "generated_node"):
                    mut_to_arguri[arg.generated_node] = arg.iri
            else:
                mut_to_arguri = None
                break


        self.bnode_queryterm, self.uri_queryterm \
                = self.__create_queryterms(self.var_to_mutable,
                                           program.old_axioms,
                                           mut_to_arg, mut_to_arguri)
        assert all(all(isinstance(x, (rdflib.URIRef, rdflib.Literal)) 
                       or x in self.var_to_mutable.values()
                       for x in ax) 
                   for ax in program.old_axioms)


    def __create_queryterms(self, var_to_mutable, old_axioms,\
            mutable_to_arg_ids: dict[rdflib.IdentifiedNode, str],\
            mutable_to_arg_uri: dict["IdentifiedNode", "URIRef"] = None,\
            ):
        """

        :TODO: theoreticly multiple mutable nodes can be mapped onto the same
            var. So var_to_mutable shouldnt work
        """
        bnode_id = 0
        resource_to_var = {node: f"?{var}" 
                           for var, node in var_to_mutable.items()}
        search_axioms = [tuple(resource_to_var.get(x, f"<{x}>") for x in ax) 
                         for ax in old_axioms]
        filter_equal = ["FILTER (%s != %s)" % pair for pair 
                        in it.permutations(resource_to_var.values(), 2)]
        assert search_axioms
        assert "?app" not in resource_to_var.values()
        #filter_axioms = ["?app [<%s> %s] %s."
        #                 % (PROLOA.id, mutable_to_arg_ids[node], var)
        #                 for node, var in resource_to_var.items()]
        filter_axioms = []
        for node, var in resource_to_var.items():
            bnode = f"?tmpbnode{bnode_id}" 
            bnode_id += 1
            filter_axioms.append("?app %s %s." %(bnode, var))
            filter_axioms.append("%s <%s> %s." %(bnode, PROLOA.id, mutable_to_arg_ids[node]))
        yield """
            SELECT %s
            WHERE {%s
            FILTER NOT EXISTS { %s }
            %s
            }""" %(" ".join(resource_to_var.values()),
                   "\n".join(f"{s} {p} {o} ." for s,p,o in search_axioms),
                   "\n".join(filter_axioms),
                   "\n".join(filter_equal),
                  )
        if mutable_to_arg_uri is None:
            yield None
            return
        filter_axioms = []
        for node, var in resource_to_var.items():
            filter_axioms.append("?app <%s> %s ." 
                                 % (mutable_to_arg_uri[node], var))
        yield """
            SELECT %s
            WHERE {%s
            FILTER NOT EXISTS { %s }
            %s
            }""" %(" ".join(resource_to_var.values()),
                   "\n".join(f"{s} {p} {o} ." for s,p,o in search_axioms),
                   "\n".join(filter_axioms),
                   "\n".join(filter_equal),
                  )



    def _find_in_graph(self, rdfgraph: rdflib.Graph) -> dict[myabc.arg, rdflib.IdentifiedNode]:
        """Find programinput in given rdfgraph

        :return: Mapping of the program-arguments as object to the
            resourcenames used
        """
        arg_to_resource: dict[myabc.arg, rdflib.IdentifiedNode]
        if getattr(self, "uri_queryterm", None):
            queryterm = self.uri_queryterm
        else:
            queryterm = self.bnode_queryterm
            #assert program in rdfgraph
        try:
            asdf = list(rdfgraph.query(queryterm))
        except pyparsing.exceptions.ParseException as err:
            raise Exception(queryterm) from err
        for found_nodes in asdf:
            arg_to_resource = {}
            for var, mutable in self.var_to_mutable.items():
                arg = self.mutable_to_arg[mutable]
                arg_to_resource[arg] = found_nodes[var]
            yield arg_to_resource

    def create_app(self, arg_to_resource, 
                   filter_newtypes: list[rdflib.IdentifiedNode] = None):
        """Create all information for an app to given input resources

        :param arg_to_resource:
        :type arg_to_resource: dict[myabc.arg, rdflib.IdentifiedNode]
        :param filter_newtypes: use this if the list of input_dict of 
            programloader is available. Just use input_dict.keys() as this
        :type filter_newtypes: list[rdflib.IdentifiedNode]
        :return: All axioms needed for the app and Resource id to use 
            in axioms for the app
        :rtype: list[rdflib.graph._TripleType], rdflib.IdentifiedNode
        :TODO: if nodes arent in old_axioms, they will be missing here
        """
        if not self.program.new_generated_arg_to_typeids:
            app_identifier = rdflib.BNode()
            axioms = [
                    (app_identifier, RDF.a, PROLOA.app),
                    (app_identifier, PROLOA.executes, self.program.iri),
                    ]
            for arg, arg_target in arg_to_resource.items():
                axioms.extend([(app_identifier, arg.iri, arg_target),
                               (arg.iri, RDF.a, PROLOA.arg),
                               ])

            yield axioms, app_identifier
        else:
            asdf_axiom = []
            if filter_newtypes is None:
                validate_type = lambda typ: True
            else: 
                validate_type = lambda typ: typ in filter_newtypes
            for arg, typeids in self.program.new_generated_arg_to_typeids.items():
                tmp = []
                asdf_axiom.append(tmp)
                for typeid in typeids:
                    if validate_type(typeid):
                        res_node = rdflib.BNode()
                        tmp.append([(arg.iri, RDF.a, PROLOA.arg),
                                    (None, arg.iri, res_node),
                                    (res_node, RDF.a, typeid),
                                    ])
            new_generate_axiom: list[list["rdflib.graph._TripleType"]]
            for new_generate_axiom in it.product(*asdf_axiom):
                app_identifier = rdflib.BNode()
                axioms = [
                        (app_identifier, RDF.a, PROLOA.app),
                        (app_identifier, PROLOA.executes, self.program.iri),
                        ]
                for arg, arg_target in arg_to_resource.items():
                    axioms.extend([(app_identifier, arg.iri, arg_target),
                                   (arg.iri, RDF.a, PROLOA.arg),
                                   ])
                q = [tuple(app_identifier if x is None else x for x in ax) 
                     for ax in it.chain(axioms, *new_generate_axiom)]
                yield q, app_identifier

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
    graphfinder: dict[myabc.program, rdfgraph_finder]
    """Mapping of used programs their graphfinders."""
    #_app_prioritiyqueue: queue.PriorityQueue[float, myabc.app]
    saved_objects: typ.Dict[rdflib.IdentifiedNode, myabc.program]
    """All available programs, arguments and other objects. Used for 
    loading additional objects from rdfgraphs.
    """

    def execute_first_app(self, rdfgraph: rdflib.Graph = None) \
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graphfinder = {}
        for pro in self.uses:
            if not pro.old_axioms:
                raise TypeError( "old axioms must be provided or tactic doesnt know when to use that program")
            self.graphfinder[pro] = rdfgraph_finder(pro)
        self._app_priorityqueue = queue.PriorityQueue()
        self._current_used_rdfgraph = rdflib.Graph()
        self.saved_objects = {}
        for program in self.uses:
            self.saved_objects[program.iri] = [program]
            for arg in program.app_args:
                self.saved_objects[arg.iri] = [arg]

    def get_priorities(self, rdfgraph: rdflib.Graph) \
            -> typ.Iterable[rdflib.graph._TripleType]:
        """Generates info, which programs can be used on the given data
        and what the priority of those programs are
        """
        pro: myabc.program
        finder: rdfgraph_finder
        arg_to_resource: dict[mybac.arg, rdflib.IdentifiedNode]
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
    def __init__(self, uri, uses: extc.info_attr_list(AUTGEN.uses)):
        super().__init__(uses=uses) #tactic_priority_organizer
        self.uri = uri
