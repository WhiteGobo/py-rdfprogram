"""Abstractclasses to annotate data, functions and methods
"""
import abc
import rdflib
import typing as typ


class arg(abc.ABC):
    """programloader.arg conforms to this
    """
    @property
    @abc.abstractmethod
    def iri(self) -> rdflib.IdentifiedNode:
        """Returns identifier of object"""

class program(abc.ABC):
    """programloader.program conforms to this
    """
    @property
    @abc.abstractmethod
    def iri(self) -> rdflib.IdentifiedNode:
        """Returns identifier of object"""

    @property
    @abc.abstractmethod
    def app_args(self) -> typ.List[arg]:
        """all used argument of this argument"""

    @property
    @abc.abstractmethod
    def example_nodes(self):
        pass
    @property
    @abc.abstractmethod
    def generated_nodes(self):
        pass
    @property
    @abc.abstractmethod
    def old_axioms(self):
        pass
    @property
    @abc.abstractmethod
    def new_axioms(self):
        pass

class mutable_resource(abc.ABC):
    """programloader.mutable_resource conforms to this
    """

class app(abc.ABC):
    """programloader.app conforms to this
    """
    def __call__(self) -> (str, typ.List[rdflib.graph._TripleType]):
        """"Prints out message from executed program and new information
        for a rdfgraph
        """

def type_control(myclass, obj):
    """Checks conformity of given object obj to class myclass"""
    if myclass==program:
        try:
            obj.example_nodes
            obj.generated_nodes
            obj.old_axioms
            obj.new_axioms
        except AttributeError as err:
            raise TypeError(obj) from err
    else:
        raise ValueError(myclass)
