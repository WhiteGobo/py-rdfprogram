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
from .programcontainer.class_programcontainer import iri_to_programcontainer, _program

class _iri_repr_class:
    def __repr__(self):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"

    def __str__(self):
        name = f"{type(self).__name__}"
        return f"<{name}:{str(self.iri)}>"


class evaluator(_iri_repr_class, useprogram.program):
    def __init__(self, iri, app_args, program_container:_program):
        """

        :TODO: remove needed_axioms cause double with useprogram.program.old_axioms
        """
        self.app_args = app_args
        self.program_container = program_container
        useprogram.program.__init__(self, iri, app_args)

    @classmethod
    def from_rdf(cls, iri,
                 app_args: extc.info_attr_list(PROLOA_NS.hasArgument),
                 ):
        #load programcontainer
        programcontainer = iri_to_programcontainer(iri)

        return cls(iri, app_args, programcontainer)

    def __call__(self, input_args: typ.Dict, node_translator, 
                 default_existing_resources):
        """Returns stderr on error and stdout on success
        """
        args, kwargs = self.get_args_and_kwargs(input_args)
        try:
            returnstring = self.program_container(*args, **kwargs)
        except ProgramFailed as err:
            raise
        new_axioms = self._find_new_axioms(returnstring, input_args, 
                                           node_translator)
        #new_axioms2 = self.get_new_axioms(returnstring, input_args, default_existing_resources, node_translator)
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
