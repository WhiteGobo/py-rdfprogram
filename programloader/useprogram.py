"""newuseprogram
This module implements all available classes for rdfloader.load_graph
"""
from . import PROLOA_NS
from . import RDF_NS
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
from .programcontainer.exceptions import ProgramFailed
from .programcontainer.class_programcontainer import iri_to_programcontainer,_program

VALID_LITERALS = (str, int, float)
"""Possible translations for literal values.

:TODO: list here, where the transformation is made
"""


class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"
        #try:
        #except AttributeError as err:
        #   raise Exception(type(self))



class program(abc.ABC, _iri_repr_class):
    """Abstract class for every program. Each program must be a callable

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
        >>> myprogram: program
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
    iri: rdflib.IdentifiedNode
    """Resource identifier in the knowledge graph"""
    example_nodes: list#[mutable_resource]
    """Resources, that describe the input for the program. Specifies, which 
    axioms must already be valid.
    """
    generated_nodes: list#[mutable_resource]
    """Resources, that describe the output of the program. Specifies, which 
    axioms will be valid after this program succeeds.
    """
    old_axioms: list[rdflib.graph._TripleType]
    """Extracted info from all example mutable nodes."""
    new_axioms: list[rdflib.graph._TripleType]
    """Extract info from all example generated nodes."""
    app_args: list["arg"]

    def __init__(self, iri, app_args):
        self.iri = iri

        self.old_axioms, self.new_axioms, self.example_nodes, self.generated_nodes = [], [], [], []
        all_axioms = []
        for a in app_args:
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
                >>>     args, kwargs = self.get_args_and_kwargs(input_args)
                >>>     returnstring = self._exe( *args, **kwargs )
                >>>     new_axioms = self.get_new_axioms(input_args, default_existing_resources, node_translator)
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

    def get_args_and_kwargs(self, input_args)\
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


    def get_new_axioms(self, returnstring, input_args, mutable_to_target)\
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


class argument_processor:
    """This class organizes, how inputnodes are treated.
    
    Following problem, we have programs that generate new files. Those
    files may need an argument that wasnt existing previous execution.
    Also there may be not connected inputs, that are still files.
    """
    #app_args: list["arg"]
    new_generated_arg_to_typeids: dict["arg", list[rdflib.IdentifiedNode]]
    """Filters which argument point to a not yet existing resource.
    To each of those resources, gives a list of all available types of 
    that resource. This is needed, when you need to load a placeholder for
    given resource.
    """

    def __init__(self, app_args):
        self.new_generated_arg_to_typeids = {}
        for myarg in app_args:
            if getattr(myarg, "example_node", False):
                continue
            try:
                for subj, pred, obj in myarg._generated_axioms:
                    if subj == myarg.generated_node and pred == RDF_NS.type:
                        self.new_generated_arg_to_typeids\
                                .setdefault(myarg, list()).append(obj)
            except AttributeError as err:
                pass


class rdfprogram(program, _iri_repr_class, argument_processor):
    """This class is for loading per rdfloader.load_from_graph .
    How the program is loaded is organized the program_container
    """
    program_container: _program

    @classmethod
    def from_rdf(cls, iri, app_args: extc.info_attr_list(PROLOA_NS.hasArgument)):
        """

        :TODO: Currently just using __init__ produces an Exception in rdfloader
        """
        return cls(iri, app_args)

    def __init__(self, iri, app_args: extc.info_attr_list(PROLOA_NS.hasArgument)):
        self.app_args = list(app_args)
        program.__init__(self, iri, app_args)
        argument_processor.__init__(self, app_args)
        #self.iri = iri
        #self.app_args = app_args
        self.program_container = iri_to_programcontainer(iri)

    def __call__(self, input_args, node_translator):
        args, kwargs = self.get_args_and_kwargs(input_args)
        returnstring = self.program_container( *args, **kwargs )

        new_axioms = self.get_new_axioms(returnstring, input_args, node_translator)
        return returnstring, new_axioms


class arg(_iri_repr_class):
    """This object describes, how an argument of the corresponding program
    can be interfaced with.
    Yet it just holds the variablename(str) or variable position(int).
    
    :var iri: iri of the corresponding node
    :var id: variablename or position
    :cvar example_node: This is a 
        placeholder for new information that is generated, if the node
        corresponding to the arg is changed

    """
    iri: rdflib.IdentifiedNode
    id: (str, int)
    example_node: "mutable_resource"
    generated_node: "mutable_resource"

    def __init__( self, iri, id: extc.info_attr( PROLOA_NS.id ), 
                 example_node: extc.info_attr( PROLOA_NS.describedBy, needed=False, at_generation=True )=None,
                 generated_node: extc.info_attr( PROLOA_NS.declaresInfoLike, needed=False, at_generation=True )=None ):
        self.iri = iri
        assert isinstance(id, (str, int)), type(id)
        self.id = id
        if example_node is not None:
            self.example_node = example_node
        if generated_node is not None:
            self.generated_node = generated_node

    def process(self):
        has_generated = []
        has_example = []
        example_axioms = []
        generated_axioms = []
        try:
            self.generated_node.info
            generated_axioms.extend(self.generated_node.info)
            has_generated.append(self.generated_node)
        except AttributeError:
            pass
        try:
            self.example_node.info
            for ax in self.example_node.info:
                if any(x in has_generated for x in ax):
                    generated_axioms.append(ax)
                else:
                    example_axioms.append(ax)
            has_example.append(self.example_node)
        except AttributeError:
            pass
        #assert not set(x.iri for x in has_example).difference(it.chain.from_iterable(example_axioms)), "not every example node is represented in axioms: %s"%(set(x.iri for x in has_example).difference(it.chain.from_iterable(example_axioms)),)
        return example_axioms, generated_axioms, has_example, has_generated
