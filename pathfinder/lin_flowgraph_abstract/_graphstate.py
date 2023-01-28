from . import _flowgraph as flowgraph
import rdflib
import rdflib.compare as comp
import itertools as it
import abc
import typing as typ
import networkx as netx
import networkx.algorithms.isomorphism as iso

class information_placeholder( abc.ABC ):
    uri: str

class program_attribute( abc.ABC ):
    generates: information_placeholder

class program( abc.ABC ):
    attributes: typ.Iterable[ program_attribute ]

    @abc.abstractmethod
    def get_inputgraph( self ):
        pass
    @abc.abstractmethod
    def get_outputgraph( self ):
        pass
    @abc.abstractmethod
    def get_inputstate( self ):
        pass
    @abc.abstractmethod
    def get_outputstate( self ):
        pass


class graphstate( flowgraph.GraphState ):
    """State exemplified, by a rdfgraph. Graph consists only of axioms 
    consisting of at minimum 1 BNode.
    Different graphstates are the same, if they are isomorph to each other.

    :var rdfgraph: Graph resembling this state
    """
    def __init__( self, rdfgraph, rename=False, immutable_resources=None ):
        from rdflib import BNode
        if immutable_resources:
            all_resources = list( it.chain( rdfgraph.all_nodes(), 
                                            rdfgraph.predicates()))
            #assert all( x in all_resources for x in immutable_resources ),
            #               "immutable resources has resources not in rdfgraph"
            self._immutable_resources = immutable_resources

        else:
            assert set(rdfgraph) == set( axiom for axiom in rdfgraph 
                                    if any( type(x) == BNode for x in axiom) )
        if rename and immutable_resources:
            raise NotImplementedError( "cant use rename and "
                                      "immutable_resources together yet" )
        elif rename:
            q = comp.to_canonical_graph( rdfgraph )
            self._hash = self.__create_hash_from_canonical_graph( q )
            nodemap = { x: BNode(i) \
                        for i, x in enumerate( sorted( \
                        filter( lambda x: type(x) == BNode, \
                               rdfgraph.all_nodes() )))\
                       }
            rdfgraph_new = rdflib.Graph()
            for s, p, o in rdfgraph:
                #rdfgraph_new.add( (s,p,o) )
                rdfgraph_new.add( (nodemap.get(s,s), nodemap.get(p,p), 
                                   nodemap.get(o,o)) )
            self.rdfgraph = comp.to_isomorphic( rdfgraph_new )
        else:
            self.rdfgraph = comp.to_isomorphic( rdfgraph )
        #self.rdfgraph = comp.to_isomorphic( rdfgraph )

    def _get_immutable_resources( self ):
        try:
            return self._immutable_resources
        except AttributeError:
            q = { *self.rdfgraph.all_nodes(), *self.rdfgraph.predicates() }
            self._immutable_resources = set( x for x in q 
                                            if type(x) != rdflib.BNode )
            return self._immutable_resources
    immutable_resources = property( fget=_get_immutable_resources )

    def _get_mutable_resources( self ):
        try:
            return self._mutable_resources
        except AttributeError:
            q = { *self.rdfgraph.all_nodes(), *self.rdfgraph.predicates() }
            self._mutable_resources = set( x for x in q 
                                        if x not in self.immutable_resources )
            return self._mutable_resources
    mutable_resources = property( fget=_get_mutable_resources )

    #def __eq__( self, other ):
    #    if type(self) != type(other):
    #        return False
    #    return self.rdfgraph == other.rdfgraph

    def __create_hash_from_canonical_graph( self, canonical_graph ):
        """This function doesnt confirm, that the given graph is canonical!!!

        """
        consistent_named_axioms = tuple( sorted( canonical_graph ) )
        return hash( consistent_named_axioms )

    def __hash__( self ):
        """

        :todo: i dont trust the namegiving of to_canonical_graph yet. have 
                to review that process
        """
        from rdflib import BNode
        try:
            return self._hash
        except AttributeError:
            hashgraph = rdflib.Graph()
            next_i = iter( range(3*len(self.rdfgraph)) )
            bnode_map = { x:x for x in self.immutable_resources }
            for a,b,c in self.rdfgraph:
                tmp_axiom = []
                for x in (a,b,c):
                    try:
                        tmp_axiom.append( bnode_map[ x ] )
                    except KeyError:
                        bnode_name = ( BNode(i) for i in next_i 
                                      if BNode(i) not in bnode_map.values() 
                                      ).__next__()
                        bnode_map[ x ] = bnode_name
                        tmp_axiom.append( bnode_name )
                hashgraph.add( tmp_axiom )
            tmpg = comp.to_canonical_graph( hashgraph )
            self._hash = self.__create_hash_from_canonical_graph( tmpg )
            return self._hash

    @classmethod
    def spawn_starting_states_from_program( cls, myprogram: program,
                                                    rename=True):
        inputgraph = myprogram.get_inputstate().rdfgraph
        return [ cls( inputgraph, rename=rename ) ]


    def find_translation_to_substate( self, other ):
        """Find translation from self to given graph

        :todo: rename to subgraph and contro everything
        """
        try:
            mapping = self._find_in_supergraph( other.rdfgraph ).__next__()
        except (AttributeError,StopIteration) as err:
            raise TypeError( "Target isnt a substate" ) from err
        return { x:y for x,y in mapping.items() }

    def find_translation_to( self, other, filter_same=True ):
        """Find translation from self to given graph

        :todo: rename to subgraph and contro everything
        """
        try:
            assert self == other
        except AssertionError as err:
            raise TypeError( "Can only find translation isomorphic "
                                "graphstates" ) from err

        try:
            mapping = self._find_in_supergraph( other.rdfgraph ).__next__()
        except (AttributeError,StopIteration) as err:
            raise TypeError() from err
        if filter_same:
            return { x:y for x,y in mapping.items() if x!=y }
        else:
            return mapping


    def _find_in_supergraph( self, subgraph: rdflib.Graph ):
        """Find translation from self to given graph

        :todo: rename to subgraph and contro everything
        """
        from rdflib.extras.external_graph_libs import \
                        rdflib_to_networkx_multidigraph
        q = rdflib.Graph()
        for axiom in subgraph:
            try:
                q.add( axiom )
            except Exception as err:
                raise Exception( axiom, q ) from err

        sub_netxgraph = rdflib_to_networkx_multidigraph( q )
        for n in sub_netxgraph.nodes():
            if type( n ) == rdflib.URIRef:
                sub_netxgraph.nodes[ n ][ "id" ] = n

        self_netxgraph = rdflib_to_networkx_multidigraph( self.rdfgraph )
        for n in self_netxgraph.nodes():
            if type( n ) == rdflib.URIRef:
                self_netxgraph.nodes[ n ][ "id" ] = n

        nm = iso.categorical_node_match("id", "")
        GM = iso.MultiGraphMatcher( self_netxgraph, sub_netxgraph, \
                                    node_match=nm )
        GM.subgraph_is_isomorphic()
        return GM.subgraph_isomorphisms_iter()


    def spawn_next_state_from_program( self, program: program, rename=True ):
        """Return all states, that can be generated, when using a program
        and this state as input

        :rtype: Iterable[ type(self) ]
        :todo: replace return with StopIteration maybe
        """
        #prestatus = comp.to_isomorphic( program.get_inputgraph() )
        prestatus = program.get_inputstate().rdfgraph
        q1 = self._find_in_supergraph( prestatus )
        try:
            peeker, q2 = it.tee( q1 )
            peeker.__next__()
        except StopIteration:
            return
        poststatus = comp.to_isomorphic( program.get_outputgraph() )

        variables: list[ rdflib.URIRef ] = [ x.generates.uri \
                                for x in program.attributes ]
        simple_in_graph = rdf_simplification_graph( prestatus, variables )
        simple_out_graph = rdf_simplification_graph( poststatus, variables )
        old_vars = simple_in_graph.get_variables()
        all_vars = simple_out_graph.get_variables()
        all_new_vars = [ n for n in all_vars if n not in old_vars ]
        overlapping_vars = [ n
                        for n in it.chain(self.rdfgraph.subjects(), 
                                          self.rdfgraph.objects())
                        if n in all_vars ]
        for n in all_new_vars:
            test_out_graph = simple_out_graph.get_data_for_nodes( 
                                          it.chain(old_vars, [n]) )
            try:
                m = self._find_in_supergraph( test_out_graph ).__next__()
                return
            except StopIteration:
                pass

        for input_mapping in q2:
            mapping = dict( input_mapping )
            input_mapping = {x:y for x,y in input_mapping.items() \
                                if type(x) == rdflib.BNode }
            for n in filter( lambda x: x not in input_mapping, 
                                overlapping_vars ):
                newnames = ( rdflib.BNode( hash(n)+x ) for x in range(1000) )
                mapping[ n ] = ( new for new in newnames 
                                if new not in all_new_vars ).__next__()
            for number_new_vars in range( 1, len(all_new_vars)+1 ):
                for new_vars in it.combinations( all_new_vars, number_new_vars):
                    all_vars = it.chain( old_vars, new_vars )
                    graph_new = simple_out_graph.get_data_for_nodes( all_vars )
                    assert len(tuple(graph_new)) > 0,"generated graph is empty"
                    for axiom in self.rdfgraph:
                        new_axiom = tuple( mapping.get(x,x) for x in axiom )
                        graph_new.add( new_axiom )
                    yield type( self )( graph_new, rename=rename ), \
                                input_mapping

    def spawn_prev_state_from_program( self, program, rename = True ):
        #prestatus = comp.to_isomorphic( program.get_inputgraph() )
        prestatus = program.get_inputstate().rdfgraph
        try:
            q1 = self._find_in_supergraph( prestatus )
            q1.__next__()
        except StopIteration:
            return
        poststatus = comp.to_isomorphic( program.get_outputgraph() )

        variables: list[ rdflib.URIRef ] = [ x.generates.uri \
                                for x in program.attributes ]
        simple_in_graph = rdf_simplification_graph( prestatus, variables )
        simple_out_graph = rdf_simplification_graph( poststatus, variables )
        old_vars = simple_in_graph.get_variables()
        all_vars = simple_out_graph.get_variables()
        all_new_vars = [ n for n in all_vars if n not in old_vars ]
        overlapping_vars = [ n
                        for n in it.chain(self.rdfgraph.subjects(), 
                                          self.rdfgraph.objects())
                        if n in all_vars ]
        found_graphs = []
        for n in all_new_vars:
            test_out_graph = simple_out_graph.get_data_for_nodes( 
                                            it.chain( old_vars, [n] ) )
            for m in self._find_in_supergraph( test_out_graph ):
                try:
                    forgot_var = ( x for x,y in m.items() if y==n ).__next__()
                    #forgot_var = m[ n ]
                except Exception as err:
                    raise Exception( m ) from err
                reduced_vars = filter( lambda x: x!=forgot_var, all_vars )
                graph_new = rdflib.Graph()
                for axiom in self.rdfgraph:
                    if forgot_var not in axiom:
                        graph_new.add( axiom )
                if _is_connected( graph_new ):
                    if graph_new not in found_graphs:
                        found_graphs.append( graph_new )
                        yield type( self )( graph_new, rename = rename )
        return



class graphstate_onlynodes( graphstate ):
    """State exemplified, by a rdfgraph. Graph consists only of axioms 
    consisting of at minimum 1 BNode. In axioms BNodes are only allowed
    as Subject and Object not as predicate.
    Different graphstates are the same, if they are isomorph to each other.
    :var rdfgraph: Graph resembling this state
    """
    def __init__( self, rdfgraph, rename=False, immutable_resources=None ):
        from rdflib import BNode
        assert all( type(p) != BNode for _,p,_ in rdfgraph )
        super().__init__( rdfgraph, rename=rename, 
                         immutable_resources=immutable_resources )


    def get_nodetype_to_nodes( self, graphstate_type=None ):
        """
        
        :param graphstate_type: return type in iterable, default None = type(self)
        :rtype: Iterable, see graphstate_type
        :returns: all graphstates with exactly one mutable resource
        """
        from rdflib import BNode
        if graphstate_type == None:
            graphstate_type = type( self )
        nodetypes = dict()
        for a,b,c in self.rdfgraph:
            if all( x not in self.immutable_resources for x in (a,c) ):
                nodetypes.setdefault( a, rdflib.Graph() )
                nodetypes.setdefault( c, rdflib.Graph() )
                #if type( a ) == BNode and type( c ) == BNode:
                pass
            elif a not in self.immutable_resources:
                #elif type( a ) == BNode:
                tmp_data = nodetypes.setdefault( a, rdflib.Graph() )
                tmp_data.add( ( BNode(a),b,c ) )
            elif c not in self.immutable_resources:
                #elif type( c ) == BNode:
                tmp_data = nodetypes.setdefault( c, rdflib.Graph() )
                tmp_data.add( ( a,b, BNode(c) ) )
        mapping = {}
        for x, g in nodetypes.items():
            tmpstate = graphstate_type( g, rename=True )
            mapping.setdefault( tmpstate, list() ).append(x)
        return mapping


    def to_reduced_state( self, nodenames ):
        """Returns graphstate, but only with mutable resources according
        to given parameter nodenames
        """
        rdfgraph = rdflib.Graph()
        helpergraph = self.to_reduced_networkx_graph()
        for x, data in helpergraph.nodes( data=True ):
            if x in nodenames:
                for axiom in data[ "type" ].rdfgraph:
                    rdfgraph.add( axiom )
        for x,y,i,data in helpergraph.edges( data=True, keys=True ):
            if x in nodenames and y in nodenames:
                predicate = data[ "type" ]
                rdfgraph.add( (x, predicate, y))
        return type(self)( rdfgraph )

    def overlapping_variablenames( self, other_graphstate ):
        """Determines, which Variable Nodes (BNodes) are overlapping
        between, this state and another state

        :type other_graphstate: type( self )
        """
        return set( self.mutable_resources )\
                .intersection( other_graphstate.mutable_resources )

    def to_reduced_networkx_graph( self, node_var="type", edge_var="type", \
                                    graphstate_type=None ):
        if graphstate_type == None:
            graphstate_type = type( self )
        nodetypes = self.get_nodetype_to_nodes()
        nodes_to_nodetype = {}
        for t, nodes in nodetypes.items():
            for n in nodes:
                nodes_to_nodetype[ n ] = t
        returngraph = netx.MultiDiGraph()
        for a,b,c in self.rdfgraph:
            for x in ( a, c ):
                if x in nodes_to_nodetype and x not in returngraph:
                    returngraph.add_node( x, \
                                    **{node_var: nodes_to_nodetype[x]})
            if all( x in nodes_to_nodetype for x in (a,c) ):
                returngraph.add_edge( a, c, **{edge_var: b} )
        return returngraph


def _is_connected( rdfgraph: rdflib.Graph ):
    from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
    from networkx.algorithms.components import is_connected
    netx_graph = rdflib_to_networkx_graph( rdfgraph )
    return is_connected( netx_graph )
    

class rdf_simplification_graph:
    """This is a graph consisting of some nodes that contains information in 
    form of rdflib.Graph . The maximal nodes are given via nodenames. the 
    maximal information is given by status_rdfgraph .
    All given nodenames, will be treated as rdflib.BNode .

    The information is saved as follows. if a nodename has a corresponding name
    in status_rdfgraph all information of this nodename is saved in a 
    rdflib.Graph in the corresponding node.
    if axiom contains 2 nodes it is saved in a edge between both nodes.
    Axioms without connection to any nodename will be discarded
    """
    _RDFINFO = "rdfinfo"
    def __init__( self, status_rdfgraph: rdflib.Graph, nodenames: list[ str ] ):
        """

        :todo: I dont think its necessary to transform the variables to BNodes
        """
        self.data = netx.Graph()
        self._q = status_rdfgraph
        #im not sure, why i did this
        #nodenames = [ rdflib.term.URIRef( x ) for x in nodenames ]
        for a,b,c in status_rdfgraph:
            if a in nodenames and c in nodenames:
                self.data.add_edge( a, c )
                tmp_datagraph = self.data.edges[ a, c ]\
                                .setdefault( self._RDFINFO, rdflib.Graph() )
                newtriple = ( rdflib.BNode(a), b, rdflib.BNode(c) )
                tmp_datagraph.add( newtriple )
            elif a in nodenames:
                self.data.add_node( a )
                tmp_datagraph = self.data.nodes[a]\
                                .setdefault( self._RDFINFO, rdflib.Graph() )
                newtriple = ( rdflib.BNode(a), b, c )
                tmp_datagraph.add( newtriple )
            elif c in nodenames:
                self.data.add_node( c )
                tmp_datagraph = self.data.nodes[c]\
                                .setdefault( self._RDFINFO, rdflib.Graph() )
                newtriple = ( a, b, rdflib.BNode(c) )
                tmp_datagraph.add( newtriple )

    def get_data_for_nodes( self, nodenames: typ.Iterable[ str ], \
                            with_edges=True ) -> rdflib.Graph :
        nodenames = list( nodenames )
        datagraph = rdflib.Graph()
        #nodenames = [ rdflib.term.URIRef( x ) for x in nodenames ]
        sg = self.data.subgraph( nodenames )
        #for n, data in it.chain( sg.nodes( data=True ), sg.edges(data=True) ):
        for _,data in sg.nodes( data=True ):
            for axiom in data[ self._RDFINFO ]:
                datagraph.add( axiom )
        if with_edges:
            for _,_,data in sg.edges(data=True):
                for axiom in data[ self._RDFINFO ]:
                    datagraph.add( axiom )
        return datagraph

    def get_variables( self ):
        return self.data.nodes()


class graphstate_to_sparql_search( graphstate ):
    """Adds functionability to search itself as subgraph in a rdflib.Graph"""
    rdfgraph: rdflib.Graph
    mutable_resources: typ.List[ rdflib.IdentifiedNode ]
    def search_in( self, target_graph:rdflib.Graph, 
                  replace_mutable_resources={} ) \
                -> typ.Iterator[ typ.Dict ]:
        """Returns an iterator over all found translations from subgraphs in
        target_graph to this graphstate's implemented rdfgraph

        :todo: remove exception handling if safe
        """
        sparql_search, trans = self._to_sparql_search_command( target_graph, \
                                                replace_mutable_resources )
        try:
            for node_to_res in target_graph.query( sparql_search ):
                yield { res: node_to_res[n] for n, res in trans.items() }
        except Exception as err:
            raise type(err)( sparql_search )

    def _to_sparql_search_command( self, target_graph=None, 
                                  replace_mutable_resources_with={} ):
        """Creates a Sparql search command to find the graphstate as
        subgraph in another rdfgraph. Mutable resources will always
        be treated as distinct resources.

        :type replace_mutable_resources_with: dict
        :param replace_mutable_resources_with: Instead, of using one as
                variable for the sparql search, use the given resource
                in the searchcode.
        :type target_graph: rdfgraph
        :param target_graph: Graph from which the translation will be extracted
        :rtype: (str, dict)
        :returns: A Sparql search command and a translator of the found
                names to the corresponding resource in the graphstate
        """
        if not target_graph:
            target_graph = self.rdfgraph
        assert all( all( isinstance( x, rdflib.IdentifiedNode ) for x in both )
                    for both in replace_mutable_resources_with.items() ),\
                    "replace_mutable_resources_with has wrong type"
        searchvariables = filter(lambda x: x not in replace_mutable_resources_with,
                                 self.mutable_resources )
        name_to_resource = { f"n{i}": r for i,r in enumerate( searchvariables)}
        names = { r: f"?{n}" for n, r in name_to_resource.items() }
        bnode_names = dict()
        def translate( term ):
            if term in names:
                return "%s" % ( names[ term ] )
            elif term in replace_mutable_resources_with:
                a,_, c = target_graph.compute_qname( replace_mutable_resources_with[ term ] )
                return f"{a}:{c}"
            elif type( term ) == rdflib.BNode:
                return bnode_names.setdefault( term, "_:%i"%(len(bnode_names)))
            else:
                a,_, c = target_graph.compute_qname( term )
                return f"{a}:{c}"
        searchterms = list( " ".join( translate(x) for x in ax ) +"."
                           for ax in self.rdfgraph )
        sparql_search = "\n".join((
                "SELECT DISTINCT %s" %(" ".join( names.values())),
                "WHERE {",
                "\n".join(searchterms),
                "}"
                ))
        return sparql_search, name_to_resource
