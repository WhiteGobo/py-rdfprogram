"""This Module enables loading resources as pythonclasses. It uses for this
the method py:meth:´rdf_loader.load_from_graph´

"""
from .rdf_loader import load_from_graph
from . import extension_classes as _ext
#from . import classloader

annotation = {
        "list": _ext.info_attr_list,
        "attr": _ext.info_attr,
        "dict": _ext.info_custom_property,
        }

