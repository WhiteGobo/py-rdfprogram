"""Base module for all needed things from programloader

"""
from . import PROLOA_NS

from .useprogram import program, mutable_resource, arg, filelink, app

from . import useprogram

input_dict = {\
        PROLOA_NS.program: useprogram.rdfprogram.from_rdf, \
        PROLOA_NS.mutable_resource: useprogram.mutable_resource,\
        PROLOA_NS.arg: useprogram.arg,\
        PROLOA_NS.link: useprogram.filelink,\
        PROLOA_NS.app: useprogram.app,\
        }
"""Use this as input for :py:meth:`rdfloader.load_from_graph`"""
