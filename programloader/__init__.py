"""Base module for all needed things from programloader

"""
from . import PROLOA_NS

from .Program import program
from .App import app
from .Filelink import filelink
from .Arg import arg


input_dict = {\
        PROLOA_NS.program: program.from_rdf, \
        PROLOA_NS.arg: arg,\
        PROLOA_NS.link: filelink,\
        PROLOA_NS.app: app,\
        }
"""Use this as input for :py:meth:`rdfloader.load_from_graph`"""
