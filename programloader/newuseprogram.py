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


def create_program(iri, app_args: extc.info_attr_list(PROLOA_NS.hasArgument)):
    """qwer

    :return: asdf
    :rtype: program
    """
    split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
    if split.scheme == "file":
        filepath = os.path.abspath( split.netloc + split.path )
        if not os.path.exists( filepath ):
            raise TypeError( filepath, "File must exist" )
        mtype, encoding = mimetypes.guess_type(filepath)
        if mtype=="text/x-python":
            return program_python(iri, filepath, app_args)

    else:
        raise NotImplementedError("only scheme file is currently implemented")


class program(abc.ABC, _iri_repr_class):
    """Abstract class for every program. Each program must be a callable
    """
    def __call__(self, *args, **kwargs):
        pass


class program_python(program, _iri_repr_class):
    """This uses as input for the commandline the method as_inputstring
    and if that fails str(element). repr cant be used because it adds \'.

    """
    def __init__(self, iri, filepath, app_args):
        assert os.path.exists( filepath )
        self.iri = iri
        self.filepath = filepath
        self.app_args = app_args

    def __call__(self, *args, **kwargs) -> str:
        commandarray = ["python", str(self.filepath)]
        for x in it.chain(args, it.chain.from_iterable(kwargs.items())):
            try:
                commandarray.append(x.as_inputstring())
            except AttributeError:
                commandarray.append(str(x))
        q = subprocess.run( commandarray, capture_output=True )
        try:
            asdf = q.check_returncode()
            program_return_str = q.stdout.decode()
        except subprocess.CalledProcessError as err:
            print( f"failed to execute {self.filepath}", file=sys.stderr)
            print( q.stderr.decode(), file=sys.stderr )
            raise Exception( "failed to execute program" ) from err
        return program_return_str


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

    def __init__( self, iri, id: extc.info_attr( PROLOA_NS.id ), 
                 example_node: extc.info_attr( PROLOA_NS.describedBy ) ):
        self.iri = iri
        assert isinstance(id, (str, int)), type(id)
        self.id = id
        if example_node is not None:
            self.example_node = example_node


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
        self._axioms, self._default_existing_resources \
                = self._find_all_axioms_and_existing_nodes()

    def _find_all_axioms_and_existing_nodes(self):
        node_to_target = {}
        default_existing_resources = set()
        for x, target in self.input_args.items():
            try:
                x.example_node
            except AttributeError:
                continue
            try:
                node_to_target[x.example_node.iri] = target.iri 
            except AttributeError as err:
                if isinstance(target, (str, float, int)):
                    node_to_target[x.example_node.iri] = rdflib.Literal(target)
                    default_existing_resources.add(rdflib.Literal(target))
                else:
                    raise Exception("expected object with iri or str, "
                                    "flow, int" ) from err
        axioms = []
        for x in self.input_args.keys():
            try:
                x.example_node.info
            except AttributeError:
                continue
            axioms.extend([tuple(node_to_target.get(x,x) for x in axiom)
                                 for axiom in x.example_node.info])
            for axiom in x.example_node.info:
                for n in axiom:
                    if n not in node_to_target:
                        default_existing_resources.add(n)
        return axioms, default_existing_resources


    def __call__( self ) -> (str, typ.List):
        for mytarget in self.input_args.values():
            try:
                mytarget.was_created()
            except AttributeError:
                pass
        rvalue = self._execute_program()
        new_axioms = self._find_new_axioms()
        return rvalue, new_axioms

    def _execute_program( self ) -> str:
        kwargs, args = {},{}
        for arg, val in self.input_args.items():
            if isinstance(arg.id, str):
                kwargs[arg.id] = val
            else:
                args[arg.id] = val
        args = [args[x] for x in sorted(args.keys())]
        return self.executes( *args, **kwargs )

    def _find_new_axioms( self ) -> typ.List:
        new_axioms: list
        existing_resources = list(self._default_existing_resources)
        updated_resources = []
        for mytarget in self.input_args.values():
            try:
                mytarget.update_change
            except AttributeError:
                continue
            if mytarget.update_change():
                updated_resources.append(mytarget.iri)
                existing_resources.append(mytarget.iri)
        for mytarget in self.input_args.values():
            try:
                if mytarget.exists():
                    existing_resources.append(mytarget.iri)
            except AttributeError:
                #is added to default_exisitin_resources in __init__
                pass
        new_axioms = [ax 
                      for ax in self._axioms 
                      if any(x in updated_resources for x in ax) 
                      and all(x in existing_resources for x in ax)]
        return new_axioms


class filelink(_iri_repr_class):
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
        if isinstance( iri, rdflib.BNode ):
            self._tempfile = tempfile.NamedTemporaryFile()
            self.filepath = self._tempfile.name
        self.update_change()
        split: urllib.parse.SplitResult = urllib.parse.urlsplit( iri )
        if split.scheme == "file":
            assert not (split.query and split.fragment)
            self.filepath = split.netloc + split.path

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
        PROLOA_NS.program: create_program, \
        PROLOA_NS.mutable_resource: mutable_resource,\
        PROLOA_NS.arg: arg,\
        PROLOA_NS.link: filelink,\
        PROLOA_NS.app: app,\
        }
"""Use this dictionary as input for rdfloader.load_from_graph"""
