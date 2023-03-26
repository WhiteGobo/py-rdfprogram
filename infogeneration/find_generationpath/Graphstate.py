import abc
import rdflib
import typing as typ

class graph_container(abc.ABC):
    """Conforms to programloader.Program.graph_container"""
    @property
    @abc.abstractmethod
    def inputgraph(self) -> rdflib.Graph:
        pass

    @property
    @abc.abstractmethod
    def outputgraph(self) -> typ.List[rdflib.Graph]:
        pass

    @property
    @abc.abstractmethod
    def var_to_argid(self) -> dict[rdflib.Variable, rdflib.IdentifiedNode]:
        pass

    @abc.abstractmethod
    def search_in(self, graph)\
            -> typ.Iterable[typ.Dict[rdflib.IdentifiedNode,
                                     rdflib.term.Variable]]:
        pass


class graph_container:
    graph: rdflib.Graph
    def __init__(self, graph, **kwargs):
        super().__init__(**kwargs)
        self.graph = graph


class state_comparer(graph_container):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._graphhash = hash(rdflib.compare.to_isomorphic(self.graph))

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return hash(self) == hash(other)

    def __hash__(self):
        return self._graphhash


class graphsearcher(graph_container):
    def search_for(self, graph)\
            -> typ.Dict[rdflib.Variable, rdflib.term.Identifier]:
        all_vars = list(filter(graph.all_nodes(),
                               lambda x: isinstance(x, rdflib.Variable)))
        VARS = ", ".join([f"?{var}" for var in all_vars])
        AXIOMS = self.inputgraph.serialize(format="ntriples")
        query = "SELECT %s WHERE{%s}"%(VARS, AXIOMS)
        for result in graph.query(query):
            yield {var: x for var, x in zip(all_vars, result)}


class transitioner(graph_container):
    def spawn_next_from_program(self, program):
        for foundtrans in self.search_for(program.inputgraph):
            for outputgraph in program.outputgraphs:
                tmptrans = dict(foundtrans)
                all_vars = filter(outputgraph.all_nodes(),
                                  lambda x: isinstance(x, rdflib.Variable))
                for x in all_vars:
                    if x not in tmptrans.values():
                        tmptrans[rdflib.BNode()] = x
                newgraph = rdflib.Graph()
                for ax in self.graph:
                    newgraph.add(ax)
                for ax in outputgraph:
                    newgraph.add((tmptrans.get(x,x) for x in ax))
                yield type(self)(newgraph)

    def spawn_prev_from_program(self, program):
        inputvars = set(filter(program.inputgraph.all_nodes(),
                               lambda x: isinstance(x, rdflib.Variable)))
        for outputgraph in program.outputgraphs:
            outputvars = set(filter(outputgraph.all_nodes(),
                                    lambda x: isinstance(x, rdflib.Variable)))
            missingvars = outputvars - inputvars
            for foundtrans in self.search_for(outputgraph):
                missingnodes = [foundtrans[var] for var in missingvars]
                newgraph = rdflib.Graph()
                for ax in self.graph:
                    if not any(x in missingnodes for x in ax):
                        newgraph.add(ax)
                yield type(self)(newgraph)


class from_program_generator(graph_container):
    @classmethod
    def from_program(cls, program: graph_container, **kwargs):
        newgraph = rdflib.Graph()
        all_vars = filter(program.inputgraph.all_nodes(),
                          lambda x: isinstance(x, rdflib.Variable))
        trans = {var: rdflib.BNode() for var in all_vars}
        for ax in program.inputgraph:
            newgraph.add((trans.get(x,x) for x in ax))
        return cls(newgraph, **kwargs)

class graphstate(transitioner, state_comparer, graph_container):
    """A holder for graphstates"""
