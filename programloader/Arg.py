from . import PROLOA_NS
from . import PROLOA_NS as PROLOA
from . import RDF_NS as RDF
import rdflib
from rdfloader import annotations as extc

class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"

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
    #example_node: mutable_resource
    #generated_node: mutable_resource

    def __init__( self, iri, id: extc.info_attr( PROLOA_NS.id ), 
                 example_data: extc.info_targetresourceinfo(PROLOA_NS.describedBy),
                 generated_data: extc.info_targetresourceinfo(PROLOA_NS.declaresInfoLike)):
        self.iri = iri
        assert isinstance(id, (str, int)), type(id)
        self.id = id

        self._generated_nodes = set(ax[0] for ax in generated_data)
        self._example_nodes = set(ax[0] for ax in example_data)
        assert len(self._generated_nodes) <= 1, self._generated_nodes
        assert len(self._example_nodes) <= 1, self._example_nodes
        try:
            self.generated_node = list(self._generated_nodes)[0]
        except IndexError:
            pass
        try:
            self.example_node = list(self._example_nodes)[0]
        except IndexError:
            pass
        valid = lambda ax: not all((ax[1]==RDF.a,
                                   ax[2]==PROLOA.mutable_resource,
                                   ))
        self._generated_axioms = list(ax for ax in generated_data if valid(ax))
        self._example_axioms = []

        for ax in example_data:
            if valid(ax):
                if any(x in self._generated_nodes for x in ax):
                    self._generated_axioms.append(ax)
                else:
                    self._example_axioms.append(ax)

    def process(self):
        return self._example_axioms, self._generated_axioms, self._example_nodes, self._generated_nodes
