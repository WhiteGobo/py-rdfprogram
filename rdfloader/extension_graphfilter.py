"""

:TODO: Change use rdflib and instead use duck typing
"""
from .extension_classes import constructor_annotation
import typing as typ
import rdflib 

class info_targetresourceinfo(constructor_annotation):
    """This annotates, that all axioms about targeted resources should be 
    found.

        >>> #ttlfile
        >>> g = Graph().parse(data=\"\"\"
        >>> root target_prop child1, child2, ... .
        >>> child1 p1, o1.
        >>> child2 p2, o2.
        >>> \"\"\")
        >>> for axioms, _empty in info_targetresourceinfo("target_prop")
        >>>                         .create_input_generator(g, "root"):
        >>>     (...)
        >>>     #axioms == [(child1, p1, o1), (child2, p2, o2)]

    This annotates, that all axioms should be found, which arent
    excluded explicitly. All axioms will be returned as axioms
    and wont be given as python-objects.

    :param ignore_uris: all axioms, which have one of these IRIs
        used as property, will be ignored.
    :type ignore_uris: list[IRI]
    :param ignore_axioms: all axioms, which uses one of these IRI-pairs
        as property and object will be ignored.
    :type ignore_axioms: list[(IRI, IRI)]
    """
    inputtype = "rdflib.graph._TripleType"
    needed = True
    at_generation = True
    def __init__(self, target_property: rdflib.IdentifiedNode):
        self.target_property = target_property

    def create_input_generator(self, rdf_graph, uri_subject):
        axioms = []
        first_layer = (uri_subject, self.target_property, None)
        for _, _, child in rdf_graph.triples(first_layer):
            for _, prop, obj in rdf_graph.triples((child, None, None)):
                axioms.append((child, prop, obj))
        def input_generator(iri_to_pythonobject):
            yield axioms, []

        return input_generator

    def find_objects(self, rdf_graph, uri_subject):
        yield []

    def find_dependencies( self, rdf_graph, uri_subject):
        return []

    def __repr__(self):
        name = ".".join((type(self).__module__, type(self).__name__))
        return f"<{name}: {self.target_property}>"

    def __str__(self):
        return f"<{type(self).__name__}: {self.target_property}>"

    def to_uri_identifier(self):
        return self
