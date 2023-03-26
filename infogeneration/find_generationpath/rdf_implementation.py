try:
    from programloader.Program import graph_container
    #uses: inputgraph:rdflib.Graph, outputgraph:list[rdflib.Graph]
    #   var_to_argid:dict[rdflib.Variable, rdflib.IdentifiedNode]
except (ImportError, ModuleNotFoundError):
    import abc
    class graph_container(abc.ABC):
        inputgraph: rdflib.Graph
        outputgraph: typ.List[rdflib.Graph]
        """all combinations of possible new axioms, generated by this program.
        Must contain the variables from inputgraph to add new axiom to an
        existing node
        """
        var_to_argid: dict[rdflib.Variable, rdflib.IdentifiedNode]

