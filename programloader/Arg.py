from . import PROLOA_NS
from . import PROLOA_NS as PROLOA
from . import RDF_NS as RDF
import rdflib
from rdfloader import annotations as extc

class _iri_repr_class:
    def __repr__( self ):
        name = f"{type(self).__module__}.{type(self).__name__}"
        return f"<{name}:{self.iri}>"

class rdftranslator:
    def to_rdf(self) -> rdflib.Graph:
        yield (self.iri, RDF.type, PROLOA.arg)
        if self.example_data:
            yield (self.iri, PROLOA.describedBy, self.example_data[0][0])
            for ax in self.example_data:
                yield ax
        if self.generated_data:
            yield (self.iri, PROLOA.declaresInfoLike, self.generated_data[0][0])
            for ax in self.generated_data:
                yield ax


class arg(rdftranslator, _iri_repr_class):
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
        """

        :TODO: just return all axioms, when asked. Because single args dont 
            know which axioms are generated and which are new
        """
        self.iri = iri
        assert isinstance(id, (str, int)), type(id)
        self.id = id
        self.example_data = list(example_data)
        self.generated_data = list(generated_data)

        self._generated_nodes = set(ax[0] for ax in self.generated_data)
        self._example_nodes = set(ax[0] for ax in self.example_data)
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
        self._generated_axioms = list(ax for ax in self.generated_data
                                      if valid(ax))
        self._example_axioms = []
        for ax in self.example_data:
            if valid(ax):
                if any(x in self._generated_nodes for x in ax):
                    self._generated_axioms.append(ax)
                else:
                    self._example_axioms.append(ax)



    def process(self):
        all_axioms = list(self._example_axioms)
        all_axioms.extend(self._generated_axioms)
        return all_axioms, self._example_nodes, self._generated_nodes
