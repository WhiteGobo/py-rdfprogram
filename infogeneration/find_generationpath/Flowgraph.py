import networkx as netx
from .Graphstate import graph_container
from .Graphstate import graphstate
from .. import reasoning
from rdflib import compare
import networkx as netx
import typing as typ

class graphcontainer:
    nodes: typ.List[graphstate]
    edges: typ.List[typ.Tuple[graphstate, graph_container, graphstate]]
    def __init__(self, nodes, edges, **kwargs):
        super().__init__(**kwargs)
        self.nodes = list(set(nodes))
        self.edges = list(set(edges))

class netx_graphcontainer(graphcontainer):
    _programid = "p"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph = netx.MultiDiGraph()
        for n in self.nodes:
            self.graph.add_node(n)
        for v1, program, v2 in self.edges:
            self.graph.add_edge(v1, v2, self._programid)



class maximal_graphs(graphcontainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        comparenodes = {n: compare.to_isomorphic(n.graph) for n in self.nodes}
        supergraph_to: dict[graphstate, list[graphstate]] = {}
        hassuperstates = []
        hassubstates = []
        subto_graph = netx.DiGraph()
        """edges symbolize source is substate to target"""
        for i, nfirst in enumerate(self.nodes):
            for nsecond in self.nodes[i+1:]:
                cg1 = comparenodes[nfirst]
                cg2 = comparenodes[nsecond]
                in_both, in_first, in_second = compare.graph_diff(cg1, cg2)
                if in_first and not in_second:
                    supergraph_to.setdefault(nfirst, []).append(nsecond)
                    hassuperstates.append(nsecond)
                    hassubstates.append(nfirst)
                    subto_graph.add_edge(nsecond, nfirst)
                elif not in_first and in_second:
                    supergraph_to.setdefault(nsecond, []).append(nfirst)
                    hassuperstates.append(nfirst)
                    hassubstates.append(nsecond)
                    subto_graph.add_edge(nfirst, nsecond)
        basestates = [n for n in self.nodes if n not in hassubstates]


class graphstate_generator(graphcontainer):
    @classmethod
    def from_programs(cls, programs: typ.List[graph_container], **kwargs):
        tobevisited = []
        edges: typ.List[typ.Tuple[graph_container, program, graph_container]]\
                = []
        for pro in graph_container:
            tmp_node = graphstate.from_program(pro)
            if tmp_node not in tobevisited:
                tobevisited.append(tmp_node)
        #tobevisited will be longer in this loop
        for node in tobevisited:
            for pro in programs:
                for newnode in node.spawn_next_from_program(pro):
                    try:
                        i = tobevisited.index(newnode)
                    except ValueError:
                        i = len(tobevisited)
                        tobevisited.append(newnode)
                    edges.append((node, pro, tobevisited[i]))
                for newnode in node.spawn_prev_from_program(pro):
                    if newnode not in tobevisited:
                        tobevisited.append(newnode)

        return cls(tobevisited, edges, **kwargs)


class flowgraph(graphstate_generator):
    """Mainclass"""
