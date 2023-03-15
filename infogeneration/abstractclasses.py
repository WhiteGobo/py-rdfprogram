"""Abstractclasses to annotate data, functions and methods
"""
import abc

class program(abc.ABC):
    """programloader.program conforms to this
    """
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

class arg(abc.ABC):
    """programloader.arg conforms to this
    """

class app(abc.ABC):
    """programloader.app conforms to this
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
