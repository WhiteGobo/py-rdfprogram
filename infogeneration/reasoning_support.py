import owlready2 as owl
import rdflib
import types
import tempfile

def reason_update(rdfgraph: rdflib.Graph,
                  iri_to_constructors: dict[rdflib.IdentifiedNode, list],
                  base_iri="http://example.com/"):
    if False:
        yield 123
    my_world = owl.World()
    onto = my_world.get_ontology("http://anonymous")
    with tempfile.NamedTemporaryFile() as f:
        with open(f.name, "w") as myf:
            myf.write(rdfgraph.serialize(format="ntriples"))
        with open(f.name, "rb") as myf:
            onto.load(fileobj=myf)
    graph = my_world.as_rdflib_graph()
    print(graph.serialize())
    print(list(onto.classes()))

    namespace_to_class = {}
    for class_iri in iri_to_constructors:
        _, ns, ending = rdfgraph.compute_qname(class_iri) 
        namespace_to_class.setdefault(ns, list()).append(ending)
    for namespace, tmpclasses in namespace_to_class.items():
        tmp_onto = my_world.get_ontology(namespace)
        with tmp_onto:
            for myclass in tmpclasses:
                tmp_class = types.new_class(myclass, (owl.Thing,))

    #myonto.imported_ontologies.append(owlready_ontology)
    #myonto.imported_ontologies.append(rdfgraph)
    print("classes: ", list(tmp_onto.classes()))
    graph = my_world.as_rdflib_graph()
    print(graph.serialize())
