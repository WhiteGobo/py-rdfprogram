"""newuseprogram
This module implements all available classes for rdfloader.load_graph
"""
from . import PROLOA_NS
from . import RDF_NS
from rdfloader import extension_classes as extc
import tempfile
import rdflib
import urllib.parse
import contextlib
import mimetypes
import os.path
import os
import abc
import subprocess
import itertools as it
import sys
import typing as typ
import collections.abc
from .programcontainer.exceptions import ProgramFailed
from .programcontainer.class_programcontainer import iri_to_programcontainer,_program

class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"
        #try:
        #except AttributeError as err:
        #   raise Exception(type(self))


class mutable_resource(_iri_repr_class):
    """A placeholder for newly generated objects, which holds axioms, which 
    are to be asserted for this new resource. 
    If the object is created, through the execution of the corresponding 
    create_program new axioms should be asserted for this resource.
    The axioms which are hold from this placeholder or are hold by another
    placeholder to this placeholder should be generated and added to
    the knowledgegraph.
    
    :var iri: (rdflib.IdentifiedNode) identifier of corresponding node
    :var info: (list[(rdflib.IdentifiedNode, )*3]) All axioms connected 
        to this node.

    """
    _is_mutable = (RDF_NS.a, PROLOA_NS.mutable_resource)
    def __init__( self, iri, info: extc.info_anyprop([],[_is_mutable]) ):
        self.iri = iri
        self.info = info


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

    """
    iri: rdflib.IdentifiedNode
    """Resource identifier in the knowledge graph"""
    example_nodes: list[mutable_resource]
    """Resources, that describe the input for the program. Specifies, which 
    axioms must already be valid.
    """
    generated_nodes: list[mutable_resource]
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
        self.app_args = app_args

        self.old_axioms, self.new_axioms, example_nodes, generated_nodes\
                = self._process_app_args(app_args)
        self.example_nodes = example_nodes
        self.generated_nodes = generated_nodes

        self.possible_new_nodes = generated_nodes
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

    def _process_app_args(self, app_args):
        has_generated = []
        has_example = []
        example_axioms = []
        generated_axioms = []
        for x in self.app_args:
            try:
                x.example_node.info
                for ax in x.example_node.info:
                    if any(x in has_generated for x in ax):
                        generated_axioms.append(ax)
                    else:
                        example_axioms.append(ax)
                has_example.append(x.example_node)
            except AttributeError:
                pass
            try:
                x.generated_node.info
                generated_axioms.extend(x.generated_node.info)
                has_generated.append(x.generated_node)
            except AttributeError:
                pass
        #assert not set(x.iri for x in has_example).difference(it.chain.from_iterable(example_axioms)), "not every example node is represented in axioms: %s"%(set(x.iri for x in has_example).difference(it.chain.from_iterable(example_axioms)),)
        return example_axioms, generated_axioms, has_example, has_generated

    def get_args_and_kwargs(self, input_args):
        for mytarget in input_args.values():
            try:
                mytarget.was_created()
            except AttributeError:
                pass

        kwargs, args = {},{}
        for arg, val in input_args.items():
            if isinstance(arg.id, str):
                kwargs[arg.id] = val
            else:
                args[arg.id] = val
        args = [args[x] for x in sorted(args.keys())]
        return args, kwargs


    def get_new_axioms(self, input_args, default_existing_resources,
                       mutable_to_target) -> typ.List:
        """
    
        :param mutable_to_target: translation of the mutable resources to
            the real inputs of the program
        :param input_args: Map of the args to the inputs
        :type input_args: typ.Dict[arg, (str, int, float, resource_link)]
        """
        new_axioms: list
        #existing_resources = list(default_existing_resources)
        existing_resources = []
        updated_resources = []
        for mytarget in input_args.values():
            try:
                mytarget.update_change
            except AttributeError:
                continue
            if mytarget.update_change():
                updated_resources.append(mytarget.iri)
                existing_resources.append(mytarget.iri)
        for mytarget in input_args.values():
            try:
                if mytarget.exists():
                    existing_resources.append(mytarget.iri)
            except AttributeError:
                pass

        all_axioms = [tuple(mutable_to_target.get(x,x) for x in axiom)
                      for axiom in self._axioms]
        not_valid = {y for y in (mutable_to_target.get(x,x) 
                     for x in self.possible_new_nodes)
                     if y not in existing_resources 
                     and isinstance(y, rdflib.IdentifiedNode)}
        new_axioms = [ax for ax in all_axioms
                      if not any(x in not_valid for x in ax)
                      and any(x in updated_resources for x in ax)]
        return new_axioms


class rdfprogram(program, _iri_repr_class):
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
        super().__init__(iri, app_args)
        #self.iri = iri
        #self.app_args = app_args
        self.program_container = iri_to_programcontainer(iri)

    def __call__(self, input_args, node_translator, default_existing_resources):
        args, kwargs = self.get_args_and_kwargs(input_args)
        returnstring = self.program_container( *args, **kwargs )

        new_axioms = self.get_new_axioms(input_args, default_existing_resources, node_translator)
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
    example_node: mutable_resource
    generated_node: mutable_resource

    def __init__( self, iri, id: extc.info_attr( PROLOA_NS.id ), 
                 example_node: extc.info_attr( PROLOA_NS.describedBy, needed=False )=None,
                 generated_node: extc.info_attr( PROLOA_NS.declaresInfoLike, needed=False )=None ):
        self.iri = iri
        assert isinstance(id, (str, int)), type(id)
        self.id = id
        if example_node is not None:
            self.example_node = example_node
        if generated_node is not None:
            self.generated_node = generated_node


class app(_iri_repr_class):
    """Commands can be executed through this callable object.

    :param input_args: Maps the arguments of the used program onto
        the inputarg that is used.
    :type input_args: dict[newuseprogram.arg, 
        (int, float, str, newuseprogram.filelink) ] 
    :param executes: Specifies, which program is used, when this
        app is executed
    :type executes: newuseprogram.program
    """
    node_translator: typ.Dict
    """Translation of the mutable resources to the resources used in this app
    """
    def __init__( self, iri, \
            input_args: extc.info_custom_property( PROLOA_NS.arg ),\
            executes: extc.info_attr( PROLOA_NS.executes ), \
            ):
        if not all( isinstance(x,(int, float, str) ) \
                or hasattr(x, "as_inputstring") for x in input_args.values() ):
            raise TypeError( input_args, "all values must be usable as "
                            "function-input" )
        self.iri = iri
        self.executes = executes
        self.input_args = input_args
        self._default_existing_resources, self.node_translator \
                = self._find_all_axioms_and_existing_nodes()

    def _find_all_axioms_and_existing_nodes(self):
        """

        :TODO: maybe move default_existing_resources to program
        """
        node_to_target = {}
        default_existing_resources = set()
        for x, target in self.input_args.items():
            translate_nodes = []
            try:
                translate_nodes.append(x.example_node)
            except AttributeError:
                pass
            try:
                translate_nodes.append(x.generated_node)
            except AttributeError:
                pass
            if hasattr(target, "iri"):
                for node in translate_nodes:
                    node_to_target[node.iri] = target.iri 
            elif isinstance(target, (str, float, int)):
                for node in translate_nodes:
                    try:
                        node_to_target[node.iri] = rdflib.Literal(target)
                    except AttributeError:
                        pass
                default_existing_resources.add(rdflib.Literal(target))
            else:
                raise Exception("expected object with iri or str, "
                                "float, int" ) from err
        for x in self.input_args.keys():
            try:
                x.example_node.info
            except AttributeError:
                continue
            for axiom in x.example_node.info:
                for n in axiom:
                    if n not in node_to_target:
                        default_existing_resources.add(n)
        for x in self.input_args.keys():
            try:
                x.generated_node.info
            except AttributeError:
                continue
            for axiom in x.generated_node.info:
                for n in axiom:
                    if n not in node_to_target:
                        default_existing_resources.add(n)
        return default_existing_resources, node_to_target


    def __call__( self ) -> (str, typ.List):
        try:
            rvalue, new_axioms = self.executes(self.input_args, \
                self.node_translator, self._default_existing_resources)
        except ProgramFailed as err:
            returnstring = err.args[1]
            new_axiom = [(self.iri, RDF_NS.a, PROLOA_NS.failedApp)]
            return returnstring, new_axiom
        return rvalue, new_axioms

class resource_link(abc.ABC):
    @abc.abstractmethod
    def update_change(self) -> bool:
        pass

class filelink(_iri_repr_class): #also resource_link but that doesnt work
    """This object is an interface for files. So if a program has to work
    on or with a file, this object enables this.

    :TODO: implement plugins for scheme
    :var filepath: (str) filepath
    :var inputstring: asdf
    """
    filepath: str
    inputstring: str
    _exist_last_check: bool
    """Use this if you want open the link as file as open(filepath, mode)"""
    _lastupdated: float
    """Last time, the filelink was updated"""
    def __init__( self, iri ):
        self.iri = iri
        split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
        if isinstance( iri, rdflib.BNode ):
            self._tempfile = tempfile.NamedTemporaryFile()
            self.filepath = self._tempfile.name
        elif split.scheme == "file":
            assert not (split.query and split.fragment)
            self.filepath = split.netloc + split.path
        self.update_change()

    def update_change(self):
        """Tests if the file was since changed, since the last time this
        was checked.
        """
        try:
            last = self._lastupdated
        except AttributeError:
            last = 0.0
        try:
            self._lastupdated = os.stat( self.filepath ).st_mtime
        except FileNotFoundError:
            self._lastupdated = 0.0
        return self._lastupdated > last

    def as_inputstring( self ):
        """Enables interfacing, with the file, through a filepath.
        The file itself can be written or read through typical fileoperations.
        """
        return self.filepath

    def __del__( self ):
        try:
            self._tempfile.close()
        except AttributeError:
            pass


input_dict = {\
        PROLOA_NS.program: rdfprogram.from_rdf, \
        PROLOA_NS.mutable_resource: mutable_resource,\
        PROLOA_NS.arg: arg,\
        PROLOA_NS.link: filelink,\
        PROLOA_NS.app: app,\
        }
"""Use this dictionary as input for rdfloader.load_from_graph"""
