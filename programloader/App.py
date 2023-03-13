import typing as typ
from rdfloader import annotations as extc
import rdflib
from . import PROLOA_NS
from . import RDF_NS
from .programcontainer.exceptions import ProgramFailed

VALID_LITERALS = (str, int, float)
"""Possible translations for literal values.

:TODO: list here, where the transformation is made
"""

class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"

class app(_iri_repr_class):
    """Commands can be executed through this callable object.

    When called always succeeds. When the program fails instead it will
    return an axiom, that this app is a failed app

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
    executes: object

    input_args: dict["Arg.arg", "Filelink.filelink"]
    """Mapping of input args to the used abstract used input"""
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
        if not all(hasattr(datalink, "exists") 
                   or isinstance(datalink, VALID_LITERALS)
                   for datalink in input_args.values()):
            for datalink in input_args.values():
                if not hasattr(datalink, "exists") or isinstance(datalink, rdflib.Literal):
                    raise Exception(datalink)
            raise TypeError(input_args)

        self.node_translator \
                = self._find_all_axioms_and_existing_nodes()

    def _find_all_axioms_and_existing_nodes(self):
        """

        :TODO: maybe move default_existing_resources to program
        """
        node_to_target = {}
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
                    node_to_target[node] = target.iri 
            elif isinstance(target, VALID_LITERALS):
                for node in translate_nodes:
                    try:
                        node_to_target[node] = rdflib.Literal(target)
                    except AttributeError:
                        pass
            else:
                raise Exception("expected object with iri or str, "
                                "float, int" ) from err
        return node_to_target


    def __call__( self ) -> (str, typ.List):
        try:
            rvalue, new_axioms = self.executes(self.input_args, \
                self.node_translator)
        except ProgramFailed as err:
            returnstring = err.args[1]
            new_axiom = [(self.iri, RDF_NS.a, PROLOA_NS.failedApp)]
            return returnstring, new_axiom
        return rvalue, new_axioms
