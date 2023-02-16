"""The evaluator class here introduced, is a pure generator for
axioms. To describe its function very rough, if it succeeds all axioms
defined for a placeholder-resources are also valid for the program input.
"""
import abc
import subprocess
import typing as typ
import urllib
import os
import mimetypes
import itertools as it
import sys
import rdflib
from . import PROLOA_NS
from . import RDF_NS
from . import useprogram
from rdfloader import extension_classes as extc
import logging
logger = logging.getLogger(__name__)
from .useprogram import ProgramFailed
from .programcontainer.class_programcontainer import iri_to_programcontainer


class _program(abc.ABC):
    """programcontainer so that you can implement a simple callable with
    args and kwargs
    """
    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> str:
        """Executes the program with given positional arguments args
        and keyword argument kwargs

        :raises ProgramFailed: if program breaks with error
        :returns: stdout of program execution will be forwarded
        """
        pass


class _iri_repr_class:
    def __repr__(self):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"

    def __str__(self):
        name = f"{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"


class evaluator(_iri_repr_class, useprogram.program):
    def __init__(self, iri, app_args, program_container:_program, needed_axioms, new_axioms ):
        """

        :TODO: remove needed_axioms cause double with useprogram.program.old_axioms
        """
        self.app_args = app_args
        self.program_container = program_container
        self.needed_axioms = needed_axioms
        self.new_axioms = new_axioms
        useprogram.program.__init__(self, iri, app_args)

    @classmethod
    def from_rdf(cls, iri,
                 app_args: extc.info_attr_list(PROLOA_NS.hasArgument),
                 ):
        #load programcontainer
        programcontainer = iri_to_programcontainer(iri)

        #load axioms
        needed_axioms = []
        new_axioms = []
        for x in app_args:
            try:
                x.example_node.info
            except AttributeError:
                continue
            try:
                needed_axioms.extend([axiom for axiom in x.example_node.info])
                new_axioms.extend([axiom for axiom in x.generated_node.info])
            except AttributeError as err:
                raise TypeError("Args need example_node and generated_node")
        return cls(iri, app_args, programcontainer, needed_axioms, new_axioms)

    def __call__(self, input_args: typ.Dict, not_needed_node_translator, 
                 default_existing_resources):
        """Returns stderr on error and stdout on success
        """
        node_translator = self._inputargs_to_nodetranslator(input_args)

        args, kwargs = self._inputargs_to_programinput(input_args)
        try:
            returnstring = self.program_container(*args, **kwargs)
        except ProgramFailed as err:
            raise
        new_axioms = self._find_new_axioms(returnstring, input_args, 
                                           node_translator)
        return returnstring, new_axioms

    def _find_new_axioms(self, returnstring, input_args, mutable_to_target):
        new_axioms = []
        try:
            g = rdflib.Graph().parse(data=returnstring)
            new_axioms.extend( g )
        except rdflib.exceptions.ParserError:
            logger.debug("Return string is not readable by rdflib")
            pass

        new_axioms.extend(tuple(mutable_to_target.get(x,x) for x in axiom)
                      for axiom in self.new_axioms)

        return new_axioms


    def _inputargs_to_programinput(self, input_args) \
            -> (list[str], dict[str, str]):
        kwargs, args = {},{}
        for arg, val in input_args.items():
            try:
                if isinstance(arg.id, str):
                    kwargs[arg.id] = val
                elif isinstance(arg.id, int):
                    args[arg.id] = val
                else:
                    raise TypeError(arg, arg.id)
            except (AttributeError, TypeError) as err:
                raise TypeError(input_args) from err

        return [args[x] for x in sorted(args.keys())], kwargs

    def _inputargs_to_nodetranslator(self, input_args):
        node_to_target = {}
        for x, target in input_args.items():
            try:
                x.example_node
            except AttributeError:
                continue
            try:
                node_to_target[x.example_node.iri] = target.iri 
                node_to_target[x.generated_node.iri] = target.iri 
            except AttributeError as err:
                if isinstance(target, (str, float, int)):
                    node_to_target[x.example_node.iri] = rdflib.Literal(target)
                    node_to_target[x.generated_node.iri] = rdflib.Literal(target)
                else:
                    raise Exception("expected object with iri or str, "
                                    "float, int" ) from err
        return node_to_target


class python_program_container(_program):
    """
    """
    def __init__(self, filepath):
        assert os.path.exists( filepath )
        self.filepath = filepath


    def __call__(self, *args, **kwargs) -> str:
        commandarray = ["python", str(self.filepath)]
        for x in it.chain(args, it.chain.from_iterable(kwargs.items())):
            try:
                commandarray.append(x.as_inputstring())
            except AttributeError:
                commandarray.append(str(x))
        q = subprocess.run(commandarray, capture_output=True)
        try:
            asdf = q.check_returncode()
            program_return_str = q.stdout.decode()
        except subprocess.CalledProcessError as err:
            #print(f"failed to execute {self.filepath}", file=sys.stderr)
            #print(q.stderr.decode(), file=sys.stderr)
            raise ProgramFailed(q.stdout.decode(), q.stderr.decode()) from err
        return program_return_str

