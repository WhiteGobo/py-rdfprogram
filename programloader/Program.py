"""newuseprogram
This module implements all available classes for rdfloader.load_graph
"""
from . import PROLOA_NS
from . import PROLOA_NS as PROLOA
from . import RDF_NS
from . import RDF_NS as RDF
from rdfloader import annotations as extc
import rdflib
import urllib.parse
import contextlib
import mimetypes
import os.path
import abc
import subprocess
import logging
logger = logging.getLogger(__name__)
"""Logger for everything programloader does"""
import itertools as it
import sys
import typing as typ
import collections.abc
from .Programcontainer.exceptions import ProgramFailed
from .Programcontainer.class_programcontainer import iri_to_programcontainer,_program
from rdflib import term
from . import Arg

VALID_INPUTS = typ.Union[str, int, float, "filelink"]
"""Possible translations for literal values.

:TODO: list here, where the transformation is made
"""

class program_basic_container:
    app_args: typ.List["arg"]
    def __init__(self, app_args, **kwargs):
        super().__init__(**kwargs)
        self.app_args = tuple(app_args)
        if not all(isinstance(arg, Arg.arg) for arg in self.app_args):
            raise TypeError(app_args)

class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"
        #try:
        #except AttributeError as err:
        #   raise Exception(type(self))


class axiom_container(program_basic_container):
    """Analyses the given app_args and saves all information about the
    input and output-axioms of this program
    """
    example_nodes: list["mutable_resource"]
    """Resources, that describe the input for the program. Specifies, which 
    axioms must already be valid.
    """
    generated_nodes: list["mutable_resource"] = None
    """Resources, that describe the output of the program. Specifies, which 
    axioms will be valid after this program succeeds.
    """
    old_axioms: list[rdflib.graph._TripleType] = None
    """Extracted info from all example mutable nodes."""
    new_axioms: list[rdflib.graph._TripleType] = None
    """Extract info from all example generated nodes."""

    possible_new_nodes: list["mutable_resource"]
    """Might be the same as generated_nodes"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.old_axioms, self.new_axioms, self.example_nodes, self.generated_nodes = [], [], [], []
        all_axioms = []
        for a in self.app_args:
            app_axioms, en, gn = a.process()
            all_axioms.extend(app_axioms)
            #self.old_axioms.extend(o)
            #self.new_axioms.extend(n)
            self.example_nodes.extend(en)
            self.generated_nodes.extend(gn)
        for ax in all_axioms:
            if any(x in self.generated_nodes for x in ax):
                self.new_axioms.append(ax)
            else:
                self.old_axioms.append(ax)

        self.possible_new_nodes = self.generated_nodes
        self._axioms = self.new_axioms

class program_callmethods(axiom_container, program_basic_container, abc.ABC):
    """Implements methods to call an executable. 

    :cvar iri: iri of this resource
    :cvar example_nodes: all mutable nodes used, when finding the input
    :cvar generated_nodes: all mutable_nodes used, when determing
        what the output looks like
    :cvar old_axioms: all needed axioms for input. Must be translated
        via example_nodes to given input resources
    :cvar new_axioms: all generated axioms from output.
    :cvar app_args: List of available input arguments for the program

    :param input_args: asdf
    :type input_args: dict
    :param node_translator: qwer
    :type node_translator: node_translator
    :param default_existing_resources: yxcv
    :type default_existing_resources: list[rdflib.IdentifiedNode]
    :return: output of the executed program and all new axioms
    :rtype: (str, typ.Iterable[rdflib.graph._TripleType])

    Example
        >>> myprogram: program_callmethods
        >>> my_information_graph: rdflib.Graph
        >>> input_args = {0:input1, "--arg":input2}
        >>> trans = {BNode("placeholder"): 
        >>>          URIRef("file://path/to/file")}
        >>> output, new_axioms = myprogram(input_args, trans, [])
        >>> for ax in new_axioms:
        >>>     my_information_graph.add(ax)

    :TODO: Move old_axioms, new_axioms, old_nodes and new_nodes 
        to argument_processor
    """

    @abc.abstractmethod
    def __call__(self, input_args, node_translator, \
            default_existing_resources) \
            -> (str, typ.Iterable[rdflib.graph._TripleType]):
        """Executes the program with given arguments. Returns
        the stdout of the program and returns all new axioms dependent
        on new generated links. See filelink for how new generated links
        are determined. The new generated links are determined by app_args
        and given node_translator.

        Example:
                >>> def __call__(self, input_args, node_translator, default_existing_resources):
                >>>     args, kwargs = self._get_args_and_kwargs(input_args)
                >>>     returnstring = self._exe( *args, **kwargs )
                >>>     new_axioms = self._get_new_axioms(input_args, default_existing_resources, node_translator)
                >>>     return returnstring, new_axioms
                >>> def _exe():
                >>>     commandarray = ["python", str(self.filepath)]
                >>>     for x in it.chain(args, it.chain.from_iterable(kwargs.items())):
                >>>         try:
                >>>             commandarray.append(x.as_inputstring())
                >>>         except AttributeError:
                >>>             commandarray.append(str(x))
                >>>     q = subprocess.run( commandarray, capture_output=True )
                >>>     try:
                >>>         asdf = q.check_returncode()
                >>>         program_return_str = q.stdout.decode()
                >>>     except subprocess.CalledProcessError as err:
                >>>         print( f"failed to execute {self.filepath}", file=sys.stderr)
                >>>         print( q.stderr.decode(), file=sys.stderr )
                >>>         raise Exception( "failed to execute program" ) from err
                >>>     return program_return_str
        """
        pass

    def _get_new_axioms(self, returnstring, input_args, mutable_to_target)\
            -> typ.List:
        """
    
        :param mutable_to_target: translation of the mutable resources to
            the real inputs of the program
        :param input_args: Map of the args to the inputs
        :type input_args: typ.Dict[arg, (str, int, float, resource_link)]
        :TODO: The query of mytarget.exists should be aligned to 
            init of filelink
        """
        new_axioms: list = []
        try:
            new_axioms.extend(rdflib.Graph().parse(data=returnstring))
        except rdflib.exceptions.ParserError:
            logger.debug("Return string is not readable by rdflib")

        existing_resources = []
        for mytarget in input_args.values():
            try:
                if mytarget.exists():
                    existing_resources.append(mytarget.iri)
            except AttributeError:
                pass

        all_axioms = [tuple(mutable_to_target.get(x,x) for x in axiom)
                      for axiom in self.new_axioms]

        not_valid = {y for y in (mutable_to_target.get(x,x) 
                     for x in self.possible_new_nodes)
                     if y not in existing_resources 
                     and isinstance(y, rdflib.IdentifiedNode)}
        logger.debug(f"not valid: {not_valid}")
        new_axioms.extend([ax for ax in all_axioms
                      if not any(x in not_valid for x in ax)])
        if not_valid:
            missing = [ax for ax in all_axioms if ax not in new_axioms]
            logger.debug("After execution of %s the resources %s werent "\
                    "existend.\nSo following axioms werent returned: %s" \
                    %(self, not_valid, missing))

        return new_axioms


class input_argument_processor:
    """Capabilities to give a executable the needed inputs"""
    def _get_args_and_kwargs(self,\
            input_args: typ.Dict[term.IdentifiedNode, term.Identifier])\
            -> (list[str], dict[str, str]):
        for mytarget in input_args.values():
            try:
                mytarget.was_created()
            except AttributeError:
                pass

        kwargs, args = {},{}
        for arg, val in input_args.items():
            if isinstance(arg.id, (str)):
                kwargs[arg.id] = val
            elif isinstance(arg.id, int):
                args[arg.id] = val
            else:
                raise TypeError(arg, arg.id, input_args)
        args = [args[x] for x in sorted(args.keys())]
        return args, kwargs


class argument_processor(program_basic_container, abc.ABC):
    """This class organizes, how inputnodes are treated.
    
    Following problem, we have programs that generate new files. Those
    files may need an argument that wasnt existing previous execution.
    Also there may be not connected inputs, that are still files.

    :TODO: This class is used for infogeneration.tactic.finder. That class 
        wont be needed anymore, when the implemented graphfinding 
        capabilities of program will be used instead. So this might 
        become OBSOLETE
    """

    @property
    def new_generated_arg_to_typeids(self)\
            -> dict["arg", list[rdflib.IdentifiedNode]]:
        """Filters which argument point to a not yet existing resource.
        To each of those resources, gives a list of all available types of 
        that resource. This is needed, when you need to load a placeholder for
        given resource.
        """
        try:
            return self.__new_generated_arg_to_typeids
        except AttributeError:
            self.__new_generated_arg_to_typeids = {}
            for myarg in self.app_args:
                if getattr(myarg, "example_node", False):
                    continue
                try:
                    for subj, pred, obj in myarg._generated_axioms:
                        if subj == myarg.generated_node and pred == RDF.type:
                            self.new_generated_arg_to_typeids\
                                    .setdefault(myarg, list()).append(obj)
                except AttributeError as err:
                    pass
            return self.__new_generated_arg_to_typeids


class graph_container(program_callmethods, program_basic_container):
    """adds all things needed to create a search for input-resources for
    this program
    """
    __var_to_arg: typ.Dict[rdflib.Variable, "arg"]
    inputgraph: rdflib.Graph
    """Inputgraph specified by self.app_args. Uses rdflib.Variable as 
    variable nodes. See self.var_to_argid for translation to app_args
    """
    outputgraphs: typ.List[rdflib.Graph]
    """List of possible outputgraphs. Uses rdflib.Variable as 
    variable nodes. See self.var_to_argid for translation to app_args
    """

    _inputvars: typ.List[str] = None

    def __init__(self, **kwargs):
        #uses: self.app_args, self.new_axioms, self.old_axioms
        super().__init__(**kwargs)
        self.__var_to_arg = dict()
        for i, myarg in enumerate(self.app_args):
            tmpvar = rdflib.Variable(f"x{i}")
            self.__var_to_arg[tmpvar] = myarg

        mut_to_var = dict()
        self._inputvars = []
        output_args = []
        for myvar, myarg in self.__var_to_arg.items():
            try:
                mut_to_var[myarg.example_node] = myvar
                self._inputvars.append(myvar)
            except AttributeError: pass
            try:
                mut_to_var[myarg.generated_node] = myvar
                output_args.append(myarg)
            except AttributeError: pass
        self.outputgraphs = self.__create_output_graphs(mut_to_var,
                                                        output_args,
                                                        self.new_axioms)
        self.inputgraph = self.__create_input_graph(mut_to_var,
                                                    self.old_axioms)


    @property
    def var_to_argid(self) -> typ.Dict[rdflib.Variable, rdflib.IdentifiedNode]:
        """Mapping of used variables in inputgraph or and outputgraphs"""
        return {v:a.iri for v,a in self.__var_to_arg.items()}


    def __create_input_graph(self, mut_to_var, old_axioms):
        """Creates input and outputgraph corresponding to information
        in app_args. 
        Notice that there may be multiple outputgraphs.
        """
        inputgraph = rdflib.Graph()
        myvar: rdflib.term.Variable
        myarg: "arg"
        for ax in old_axioms:
            inputgraph.add((mut_to_var.get(x,x) for x in ax))
        return inputgraph

    def __create_output_graphs(self, mut_to_var, output_args, new_axioms):
        """
        :TODO: doesnt respect tmp_args
        """
        outputgraphs = []
        basic_information = list(new_axioms)
        for i in range(1, len(output_args)+1):
            for tmp_args in it.combinations(output_args, i):
                tmp_outputgraph = set()
                outputgraphs.append(tmp_outputgraph)
                for ax in new_axioms:
                    if all(mut_to_var[x] for x in ax if x in mut_to_var):
                        tmp_outputgraph.add(tuple(mut_to_var.get(x,x)
                                                  for x in ax))
        return tuple(outputgraphs)


class inputgraphfinder(program_basic_container, abc.ABC):
    """gives methods to find the inputgraph within a given graph"""
    @property
    @abc.abstractmethod
    def _inputvars(self) -> typ.List[str]:
        """Returns all variables used in inputgraph"""

    def create_possible_apps(self, argid_to_resource: typ.Dict[rdflib.IdentifiedNode, rdflib.term.Identifier],
                             store=None,
                             newapp: rdflib.IdentifiedNode=None):
        """Searches in given graph for possible new apps of this program.
        Returns an informationgraph with new apps and all temporary nodes
        needed as input

        :param argid_to_resource: inputparameters for which a new app should
            be created.
        :type argid_to_resource: typing.Dict[rdflib.IdentifiedNode,
            rdflib.term.Identifier]
        :TODO: Rework newnode axiom addition. Currently only creates 
            missing nodes as proloa:filelink
        """
        assert set(argid_to_resource) \
                == {self.var_to_argid[var] for var in self._inputvars}
        g = rdflib.Graph(store=store) if store is not None else rdflib.Graph()
        if newapp is None:
            newapp = rdflib.BNode()
        g.add((newapp, RDF.type, PROLOA.app))
        argid_to_res = dict(argid_to_resource)
        newnodes = []
        for arg in self.app_args:
            argid = arg.iri
            if argid not in argid_to_res:
                tmp_node = rdflib.BNode()
                newnodes.append(tmp_node)
                argid_to_res[argid] = tmp_node
                g.add((tmp_node, RDF.type, PROLOA.link))
        for argid, res in argid_to_res.items():
            g.add((newapp, argid, res))
        return g

    def _create_filter_existing_app(self, rdfgraph: rdflib.Graph,
                                    app_var="app") -> str:
        if all(isinstance(argid, rdflib.URIRef) 
               for argid in self.var_to_argid.values()):
            return " .\n".join((f"?{app_var} <{arg}> ?{var}")
                               for var, arg in self.var_to_argid.items()),
        else:
            raise NotImplementedError("This only works currently, when "\
                    "argument arg are given as URI. So no BNodes currently"\
                    "supported")

    def search_in(self, rdfgraph: rdflib.Graph, limit=None)\
            -> typ.Iterable[typ.Dict[rdflib.IdentifiedNode,
                                     rdflib.term.Identifier]]:
        """searches possible resources usable as input for program"""

        filter_equal = ("FILTER (%s != %s)" % pair for pair 
                        in it.permutations(self._inputvars, 2))
        # ?app is some common app. app should be in self.var_to_argid
        filter_existing_app: str = self._create_filter_existing_app(rdfgraph)

        VARS = ", ".join([f"?{var}" for var in self._inputvars])
        AXIOMS = self.inputgraph.serialize(format="ntriples")[:-1] #deletes \n at end
        FILTER_EQUAL = "\n".join(filter_equal)
        FILTER_APPS = "FILTER NOT EXISTS {\n%s\n}" % (filter_existing_app)
        LIMIT = " LIMIT %i" % (limit) if limit is not None else ""
        query = f"SELECT {VARS}\nWHERE {{\n{AXIOMS}{FILTER_EQUAL}"\
                f"\n{FILTER_APPS}\n}}{LIMIT}"

        logger.debug("Used query: %s" %(query))
        for result in rdfgraph.query(query):
            yield {self.var_to_argid[var]: obj
                   for var, obj in zip(self._inputvars, result)}


class program(_iri_repr_class, 
              input_argument_processor, 
              argument_processor, 
              #program_callmethods, 
              graph_container,
              inputgraphfinder,
              ):
    """This class is for loading per rdfloader.load_from_graph .
    How the program is loaded is organized the program_container

    :param input_args: q
    :type input_args: typing.Dict["arg", VALID_INPUTS]
    :param node_translator: q
    :type node_translator: typing.Dict[term.IdentifiedNode, term.Identifier])
    """
    program_container: _program

    #iri: str = None
    #app_args: typ.List["arg"] = None

    @classmethod
    def from_rdf(cls, iri, app_args: extc.info_attr_list(PROLOA_NS.hasArgument)):
        """

        :TODO: Currently just using __init__ produces an Exception in rdfloader
        """
        return cls(iri, app_args)

    def __init__(self, iri, app_args: extc.info_attr_list(PROLOA_NS.hasArgument)):
        self.iri = iri
        super().__init__(app_args=app_args)
        self.program_container = iri_to_programcontainer(iri)

    def __call__(self, input_args: typ.Dict["arg", VALID_INPUTS], 
                 node_translator: typ.Dict[term.IdentifiedNode, term.Identifier]):
        args, kwargs = self._get_args_and_kwargs(input_args)
        returnstring = self.program_container( *args, **kwargs )

        new_axioms = self._get_new_axioms(returnstring, input_args, node_translator)
        return returnstring, new_axioms
