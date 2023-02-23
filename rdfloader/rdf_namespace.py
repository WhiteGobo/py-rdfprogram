import rdflib

class rdf_namespace:
    def __init__(self, rdfgraph: rdflib.Graph, namespace):
        self.rdfgraph = rdfgraph
        for node in rdfgraph.subjects():
            if isinstance(node, rdflib.URIRef):
                short, prefix, suffix = rdfgraph.compute_qname(node)
                setattr(self, suffix, node)

    @classmethod
    def from_file(cls, filepath, namespace = None):
        g = rdflib.Graph().parse(filepath)
        if namespace is None:
            q = set()
            for node in g.subjects():
                short, prefix, suffix = g.compute_qname(node)
                q.add(prefix)
            assert len(q) == 1, "multiple possible namespaces found"
            namespace = q.pop()
        return cls(g, namespace)
