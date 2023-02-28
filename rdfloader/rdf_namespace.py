import rdflib

class rdf_namespace:
    """Will hold all found attributes to namespace as attribute."""

    _suffixes: list
    """Holds all found attributes"""
    
    def __init__(self, rdfgraph: rdflib.Graph, namespace):
        self.rdfgraph = rdfgraph
        self._suffixes = []
        for node in rdfgraph.subjects():
            if isinstance(node, rdflib.URIRef):
                short, prefix, suffix = rdfgraph.compute_qname(node)
                setattr(self, suffix, node)
                self._suffixes.append(suffix)

    @classmethod
    def from_file(cls, filepath, namespace = None, **kwargs):
        """Load information about namespace from given file.
        Uses rdflib.Graph as parser for given file.

        :param kwargs: will be forwarded to rdflib.Graph.parse
        """
        g = rdflib.Graph().parse(filepath, **kwargs)
        if namespace is None:
            q = set()
            for node in g.subjects():
                short, prefix, suffix = g.compute_qname(node)
                q.add(prefix)
            assert len(q) == 1, "multiple possible namespaces found"
            namespace = q.pop()
        return cls(g, namespace)
