import rdflib
import networkx as netx
import networkx.algorithms.isomorphism as iso
import typing as typ
import abc
from . import _graphstate as graphstate
from . import _flowgraph as flowgraph
BASE_URI_auto = "http://program/automaton#"
URI_typeof = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
URI_generation_target = rdflib.URIRef( f"{BASE_URI_auto}generation_target" )
URI_generation_successful = rdflib.URIRef( f"{BASE_URI_auto}generation_successful" )

def find_missing_nodes( wholegraph: rdflib.Graph ):
    for x,_,_ in wholegraph.triples(( None, URI_typeof, URI_generation_target)):
        if (x, URI_typeof, URI_generation_successful) not in wholegraph:
            yield x

class rdfgraph_flowgraph( flowgraph.flowgraph ):
    def __init__( self, states: flowgraph.GraphState, flowedges: flowgraph.FLOWGRAPH_EDGEMAP ):
        super().__init__( states, flowedges )

    def _get_nodetypes( self ):
        """Returns all generatable nodes. Each node is characterized by 
        a graphstate consisting of one rdflib.BNode and all connected 
        immutable axioms.
        Immutable axioms means, only the the generatable node is a Bnode
        everything else is a URI.
        """
        nodetypes = set()
        for s in self._datacontainer:
            a = s.get_nodetype_to_nodes()
            nodetypes.update( a.keys() )
        return nodetypes

    def _get_superstates_to( self ):
        """Returns a map of every graphstate to every other graphstate, which
        is superstate to the prior.
        """
        def is_contained( s1, s2 ):
            mappings = s1._find_in_supergraph( s2.rdfgraph )
            try:
                mappings.__next__()
                return True
            except StopIteration:
                return False
        #has_superstate = []
        superstate_to = {}
        for state1, state2 in it.combinations( self._datacontainer.nodes(), 2 ):
            if is_contained( state1, state2 ):
                superstate_to.setdefault( state1, [] ).append( state2 )
                #has_superstate.append( state2 )
            elif is_contained( state2, state1 ):
                superstate_to.setdefault( state2, [] ).append( state1 )
                #has_superstate.append( state1 )
        return superstate_to
        #return [ s for s in self._datacontainer.nodes() if s not in has_superstate ]
    def _get_superstates( self ):
        """Returns all graphstates, which are not contained as subgraph in
        other graphstates in this flowgraph
        """
        superstates_to = self._get_superstates_to()
        has_superstate = set( it.chain.from_iterable(superstates_to.values()))
        return [ s for s in self._datacontainer.nodes() 
                            if s not in has_superstate ]

    def find_superstates_to( self, input_graphstate ):
        assert type( input_graphstate ) == type(iter( self._datacontainer.nodes()).__next__())
        def is_substate_to( substate, superstate ):
            mappings = superstate._find_in_supergraph( substate.rdfgraph )
            try:
                mappings.__next__()
                return True
            except StopIteration:
                return False
        for state2 in self._datacontainer.nodes():
            if is_substate_to( input_graphstate, state2 ):
                yield state2


    def find_partgraphs( self, wholegraph, minimal_graph_size=1 ):
        """Uses superstates in this flowgraph to find subgraphs to
        these superstates in wholegraph.
        For superstates see self._get_superstates.
        Subgraphs of the wholegraph are node-induced subgraphs from
        wholegraph.

        :param wholegraph: Wholegraph, for which partgraphs will be
                extracted. Partgraphs will only be represented as set of 
                nodes. See returnvalue for more information
        :param minimal_graph_size: minimal size of extracted partgraphs
                from wholegraph
        :type minimal_graph_size: int
        :rtype: Dict[ flowgraph.GraphState, List[ Dict[Node, Node] ] ]
        :returns: Mapping of all superstates in this flowgraph to a
                translation nodes to nodes. The translation translates
                from the nodes in the superstate to nodes in wholegraph.
                Partgraphs extracted from wholegraph are present as values
                of each translation.
        """
        superstates = self._get_superstates()
        graphstate_type = type( superstates[0] )
        nodetypes = list( self._get_nodetypes() )
        immutable_resources = set( it.chain.from_iterable( 
                                    s.immutable_resources for s in superstates))
        node_var, edge_var = "n", "e"
        nm = iso.categorical_node_match( node_var, "" )
        em = iso.categorical_multiedge_match( edge_var, "" )
        reduced_graphs = { s.to_reduced_networkx_graph( node_var, edge_var ): s
                                    for s in superstates }
        graphstate_whole = graphstate_type( wholegraph, \
                                    immutable_resources=immutable_resources )
        reduced_wholegraph = graphstate_whole.to_reduced_networkx_graph( 
                                    node_var=node_var, edge_var=edge_var )
        assert len( reduced_wholegraph.nodes() ) > 0
        maxdatastate_to_partgraph_mapping = {}
        assert all( x in nodetypes for x in 
                                    graphstate_whole.get_nodetype_to_nodes() ),\
                                    "Cant create given graph with this "\
                                    "flowgraph, cant create nodes: "
        for max_datastate in reduced_graphs:
            partgraphs = [ reduced_wholegraph ]
            visited_partgraphs = [ set( reduced_wholegraph.nodes()) ]
            for partgraph in partgraphs:
                GM = iso.MultiDiGraphMatcher( max_datastate, partgraph, \
                            node_match=nm, edge_match=em )
                if GM.subgraph_is_isomorphic():
                    map_partgraph_to_maxdatastate \
                            = GM.subgraph_isomorphisms_iter().__next__()
                    current_superstate = reduced_graphs[ max_datastate ]
                    tmp_list = maxdatastate_to_partgraph_mapping\
                            .setdefault( current_superstate, [] )
                    tmp_list.append( map_partgraph_to_maxdatastate )

                else: #reduce nodenumber and try smaller subgraphs
                    partgraph_nodes = set( partgraph.nodes() )
                    if len( partgraph_nodes ) <= minimal_graph_size:
                        continue
                    for n in partgraph_nodes:
                        new_partgraph_nodes = set( x for x in partgraph_nodes 
                                                if x!= n )
                        if new_partgraph_nodes not in visited_partgraphs:
                            visited_partgraphs.append( new_partgraph_nodes )
                            new_partgraph = partgraph.subgraph( new_partgraph_nodes )
                            if netx.is_weakly_connected( new_partgraph ):
                                partgraphs.append( new_partgraph )

        return maxdatastate_to_partgraph_mapping

    def _get_generators_to( self ):
        paths = netx.shortest_paths.shortest_path( self._datacontainer )
        generators = {}
        for x, ys in paths.items():
            #for y, path in ys.items():
            for y in ys:
                if x != y: #path to itself is always there
                    generators.setdefault( y, [] ).append( x )
        return generators

    def _find_minimal_generating_graphstates( self ):
        """Gives minimal graphstates for creation of given graphstate.
        Filters the possible graphstates, so that not one of the 
        returned graphstates is a supergraph to another graphstate.
        For superstates see self._get_superstates.

        :todo: try to transfer this method, to parentclass
        :rtype: Iterable[ graphstate ]
        :returns: yields all minimal graphstates, which, can be used 
                to create given graphstates.
        """
        def invert_dict( mydict ):
            inv_dict = {}
            for x, mylist in mydict.items():
                for y in mylist:
                    inv_dict.setdefault( y, [] ).append( x )
            return inv_dict
        superstates_to = self._get_superstates_to()
        superstates_from = invert_dict( superstates_to )
        #generators_to = self._get_generators_to()
        generators_to = self._get_generators_to()
        for x in self._datacontainer.nodes():
            tmp_minimal = True
            for y in generators_to.get( x, [] ):
                if x in superstates_from.get( y, [] ):
                    tmp_minimal = False
                    break
            if tmp_minimal:
                yield x

    def complete_datagraph( self, wholegraph, ignore_nodes=[ URI_generation_target, URI_generation_successful ] ):
        """Filters the given graph to all resources, that are interesting 
        in the terms of this flowgraph. So that only nodes are inside this, 
        that are either missing or usable by any program, used in this 
        flowgraph.
        Finds all creatable nodes, by the programs in this flowgraph.
        Finds all subgraphs, used when creating missing resources.

        """
        axiom_target = (None, URI_typeof, URI_generation_target)
        axiom_successful = lambda a: (a, URI_typeof, URI_generation_successful)
        missing_nodes = [ a for a,_,_ in wholegraph.triples( axiom_target )
                         if axiom_successful( a ) not in wholegraph ]

        filtered_wholegraph = rdflib.Graph()
        for axiom in wholegraph:
            if not any( x in ignore_nodes for x in axiom ):
                filtered_wholegraph.add( axiom )


        partgraphs = self.find_partgraphs( filtered_wholegraph )
        get_generators_to = self._get_generators_to()
        mini = list( self._find_minimal_generating_graphstates() )
        input_outputgraphs = []
        for a, translators in partgraphs.items():
            for translator in translators:
                a_nodes = a.to_reduced_networkx_graph().nodes()
                targetgraph_nodes = [ translator[n] for n in a_nodes 
                                        if n in translator ]
                gens = get_generators_to[ a ]
                for x in gens:
                    state_trans = a.find_translation_to_substate( x )
                    anti_state_trans = { o:i for i,o in state_trans.items() }
                    x_nodes = x.to_reduced_networkx_graph().nodes()
                    tmp_nodes = [ anti_state_trans[x] for x in x_nodes 
                                        if x in anti_state_trans ]
                    inputgraph_nodes = [ translator[n] for n in tmp_nodes
                                        if n in translator ]
                    #if can find all needed nodes in wholegraph
                    if len( inputgraph_nodes ) == len( x_nodes ):
                        input_outputgraphs.append( (inputgraph_nodes, targetgraph_nodes) )
        input_outputgraphs.sort( key = lambda x: 
                                ( len(x[0])-len(x[1]), len(x[0]) ) )
        return input_outputgraphs, missing_nodes, filtered_wholegraph
        return program_iterator( self, input_outputgraphs, missing_nodes, filtered_wholegraph )

        for _ in range( len(missing_nodes) ): #len(missing_nodes) is snapshot
            if len(missing_nodes) == 0:
                break
            for pair in input_outputgraphs:
                input_nodes, output_nodes = pair
                if not any( n in missing_nodes for n in output_nodes ):
                    input_outputgraphs.remove( pair )
            for input_nodes, output_nodes in input_outputgraphs:
                if any( n in wholegraph_creatable_nodes for n in input_nodes ):
                    continue
                new_info = create_new_info( in_graph, out_graph )
                missing_nodes = [ x for x in missing_nodes if x not in new_info ]

class program_iterator( typ.Iterator, abc.ABC ):
    def __init__( self, flowgraph, input_outputgraphs, missing_nodes, used_wholegraph ):
        assert all( len(x) != 0 for x,_ in input_outputgraphs )
        assert all( len(y) != 0 for _,y in input_outputgraphs )
        self.input_outputgraphs = input_outputgraphs
        self.missing_nodes = missing_nodes
        self.used_wholegraph_state = flowgraph.graphstate( used_wholegraph )
        self.flowgraph = flowgraph

    def __next__( self ):
        if len( self.missing_nodes ) == 0:
            raise StopIteration()
        for pair in self.input_outputgraphs:
            input_nodes, output_nodes = pair
            if not any( n in self.missing_nodes for n in output_nodes ):
                input_outputgraphs.remove( pair )
        for input_nodes, output_nodes in self.input_outputgraphs:
            if any( n not in self.missing_nodes for n in input_nodes ):
                continue
            try:
                new_info = self._create_new_info( input_nodes, output_nodes )
            except Exception as err:
                raise Exception( input_nodes, output_nodes ) from err
            self.missing_nodes = [ x for x in self.missing_nodes \
                                    if x not in new_info ]
            return new_info
        raise Exception()
    
    def _create_new_info( self, input_nodes, output_nodes ):
        """This function may work indefinitly
        """
        assert input_nodes
        assert output_nodes
        in_graph = self.used_wholegraph_state.to_reduced_state( input_nodes )
        out_graph = self.used_wholegraph_state.to_reduced_state( output_nodes )
        superstates = tuple( self.flowgraph.find_superstates_to( out_graph ) )
        current_graph = in_graph
        while current_graph not in superstates:
            c = self.flowgraph.get_possible_processes( current_graph, 
                                            superstates,
                                            neighbouring_graphstates=False )
            for input_translation, program in c:
                #reduce graph to input_trans
                new_graph = self.execute_program( current_graph, 
                                                     input_translation, 
                                                     program )
                #extend newgraph with all previous reduced nodes
                assert current_graph.overlapping_variablenames( new_graph ), current_graph.overlapping_variablenames( new_graph )
                current_graph = new_graph

                break
            input( "next?" )
        raise Exception( "this method will fail, because there is no way implemented yet, to know how to find a way from one graphstate to another, if they are not directly connected by a program" )

    @classmethod
    def from_flowgraph( cls, flowgraph, wholegraph ):

        input_outputgraphs, missing_nodes, filtered_wholegraph = flowgraph.complete_datagraph( wholegraph )
        return cls( flowgraph, input_outputgraphs, missing_nodes, filtered_wholegraph )

    @abc.abstractmethod
    def execute_program( self, graphstate, input_translation, program:graphstate.program ) -> rdflib.Graph:
        #( self, program_out_to_graphstate, program:graphstate.program ) -> rdflib.Graph:
        pass



def complete_datagraph( myflowgraph, wholegraph ):
    """Tries to fill all nodes in wholegraph with data. Uses myflowgraph to
    create automaticly all needed programs to do this.

    :type wholegraph: rdflib.Graph
    :type myflowgraph: flowgraph
    """
    create_new_info = flowgraph_executioner( myflowgraph )

    maxpartgraphs = find_maximal_datastates_containing_partgraphs( \
                                            myflowgraph, wholegraph )
    #assert maxpartgraphs, "empty maxgraphs"

    generatable_with = find_possible_generators( maxpartgraphs, \
                                            myflowgraph, wholegraph )

    #newwholegraph = complete_data_with_info( wholegraph, generatable_with,myflowgraph )
    all_nodes = list( wholegraph.all_nodes() )
    missing_nodes = list( find_missing_nodes( wholegraph ) )
    #for _ in range( len(missing_nodes) ):
    while True:
        if len( missing_nodes ) == 0:
            break
        for sourcenodes, targetnodes in get_sorted_inputoutputgraphs( missing_nodes, wholegraph, myflowgraph ):
            in_graph = None
            out_graph = None
            new_info = create_new_info( in_graph, out_graph )
            missing_nodes = [ x for x in missing_nodes if x not in new_info ]

    return newwholegraph

class flowgraph_executioner:
    def __init__( self, myflowgraph ):
        pass

def find_maximal_datastates_containing_partgraphs( myflowgraph, wholegraph ):
    pass

def find_possible_generators( maxpartgraphs, myflowgraph, wholegraph ):
    pass

def get_sorted_inputoutputgraphs( missing_nodes, wholegraph:rdflib.Graph, myflowgraph ):

    border_nodes = _get_border( wholegraph, missing_nodes )
    inputoutputgraphs = set( it.chain.from_iterable(\
            ( (sourcenodes, targetnodes) \
            for sourcenodes, targetnodes in generatable_with[ nextnode ] \
            if sourcenodes.issubset( completed_nodes ) )
            for nextnode in borderlist
            ))
    inputoutputgraphs = it.chain.from_iterable( \
            ( (source, frozenset(target_connected_nodes)) \
            for target_connected_nodes in split_output( source, target )\
            if len(set(borderlist).intersection(target_connected_nodes))>0 )\
            for source, target in inputoutputgraphs )
    sortkey = lambda x: ( len(x[0])-len(x[1]), len(x[0]) )
    tried_nodepairs = []
    for sourcenodes, targetnodes in sorted( inputoutputgraphs, key= sortkey):
        if ( sourcenodes, targetnodes ) not in tried_nodepairs:
            tried_nodepairs.add( (sourcenodes, targetnodes) )
            yield sourcenodes, targetnodes


###########################################
###old
######################################


#from ..find_process_path import datastate_from_graph, \
#                            datastate, \
#                            datastate_not_connected_error
#from ..linear_factorybranch import complex_linear_factory_leaf as comp_factleaf
#from ..linear_factorybranch import FailstateReached, NoPathToOutput, \
        #                            DataRescueException
#from ..class_datastate import datastate, FindSubsetError
#from ..class_datagraph import datagraph
import networkx as netx
import logging
logger = logging.getLogger( __name__ )
#from ..constants import \
        #        DATAGRAPH_DATATYPE as DATATYPE
from typing import Dict, List
#from .. import processes as dg_pr
import itertools as it

from typing import Tuple, Hashable, Dict, Iterable


Nodelist = Tuple[ Hashable ]


def find_maximal_datastates_containing_partgraphs_old( myflowgraph, wholegraph ):
    """Searches for subgraphs of given wholegraph, that are contained 
    in myflowgraph.

    :type myflowgraph: flowgraph
    :type wholegraph: datagraph
    :rtype: Dict[ Tuple[ Nodelist, datastate ], datagraph ]
    """
    max_datastate_list = myflowgraph.get_maximal_datastates()
    max_datastates_to_partgraphs: Dict[ datastate, List[datagraph]] = {}
    node_to_datatype = wholegraph.get_node_datatypes()
    for max_datastate in max_datastate_list:
        partgraphs = [ wholegraph ]
        visited_partgraphs = [ set( wholegraph.nodes()) ]
        for partgraph in partgraphs:
            try:
                partstate = datastate.from_datagraph( partgraph )
                translist = max_datastate.find_translation_to_subset( partstate )
                for i in translist:
                    max_partgraph_nodes = frozenset( i.values() )
                    tmplist = max_datastates_to_partgraphs.setdefault( \
                                    (max_partgraph_nodes, max_datastate), list() )
                continue
            except FindSubsetError:
                partgraph_nodes = set( partgraph.nodes() )
                if len( partgraph_nodes ) == 1:
                    continue
                partgraph_edges = set( partgraph.edges() )
                for n in partgraph_nodes:
                    newnodes = partgraph_nodes.difference( [n] )
                    newedges = [ (v1, v2, etype) \
                            for v1, v2, etype in partgraph_edges \
                            if n not in (v1, v2) ]
                    if is_connected( newnodes, newedges ):
                        newpartgraph = datagraph.from_typedeclarations(\
                                {n:node_to_datatype[n] for n in newnodes }, \
                                newedges )
                        partgraphs.append( newpartgraph )
    return max_datastates_to_partgraphs


def find_possible_generators_old( maxpartgraphs, myflowgraph, wholegraph ):
    """

    :type maxpartgraphs: Iterable[ Tuple[ Nodelist, datastate ] ]
    :rtype: Dict[ hashable, Iterable[ Tuple[ Nodelist, Nodelist ] ]]
    """
    generatable_with = {}
    for partgraph_nodeset, max_datastate in maxpartgraphs:
        partgraph = wholegraph.subgraph( partgraph_nodeset )

        minimal_states = myflowgraph.get_minimal_datastates_for_creation( \
                                                            max_datastate )
        for minstate in minimal_states:
            partgraph_state = datastate.from_datagraph( partgraph )
            try:
                trans = partgraph_state.find_translation_to_subset( minstate )
            except FindSubsetError:
                continue
            minimal_nodes = trans[0].keys()
            generatable_nodes = tuple( set( partgraph.nodes() )\
                                .difference( minimal_nodes ))
            for newnode in generatable_nodes:
                tmplist = generatable_with.setdefault( newnode, list() )
                tmplist.append( (frozenset( minimal_nodes ),partgraph_nodeset) )
    return generatable_with



def complete_datagraph_old( myflowgraph, wholegraph ):
    """Tries to fill all nodes in wholegraph with data. Uses myflowgraph to
    create automaticly all needed programs to do this.

    :type wholegraph: datagraph
    :type myflowgraph: flowgraph
    """
    logger.debug( "wholegraph, nodes to datatype: %s "\
                    %( wholegraph.get_node_datatypes() ))

    maxpartgraphs = find_maximal_datastates_containing_partgraphs( \
                                            myflowgraph, wholegraph )
    assert maxpartgraphs, "empty maxgraphs"

    generatable_with = find_possible_generators( maxpartgraphs, myflowgraph, wholegraph )

    newwholegraph = complete_data_with_info( wholegraph, generatable_with,myflowgraph )
    return newwholegraph



def complete_data_with_info( wholegraph, generatable_with, myflowgraph ):
    """

    :type generatable_with: Dict[ hashable, Iterable[ Tuple[ Nodelist, Nodelist ] ]]
    """
    missing_nodes = set( wholegraph.nodes() ).difference(wholegraph.keys() )
    if any( v not in generatable_with for v in missing_nodes ):
        raise ValueError( "Cant generate all missing data. Missing: %s, %s" \
                    %( [v for v in missing_nodes if v not in generatable_with]))
    helperedges = wholegraph.edges()
    def split_output( sourcenodes, targetnodes ):
        generated = set( targetnodes ).difference( sourcenodes )
        split = split_connected_subgraphs( generated, helperedges )
        for gen_part in split:
            yield set( gen_part ).union( sourcenodes )
    while len( wholegraph.keys() ) < len( wholegraph.nodes() ):
        borderlist = list( wholegraph.get_completed_datanode_border( \
                                                not_completed_nodes=True))
        completed_nodes = wholegraph.keys()
        tried_nodepairs = set()
        inputoutputgraphs = set( it.chain.from_iterable(\
                ( (sourcenodes, targetnodes) \
                for sourcenodes, targetnodes in generatable_with[ nextnode ] \
                if sourcenodes.issubset( completed_nodes ) )
                for nextnode in borderlist
                ))
        inputoutputgraphs = it.chain.from_iterable( \
                ( (source, frozenset(target_connected_nodes)) \
                for target_connected_nodes in split_output( source, target )\
                if len(set(borderlist).intersection(target_connected_nodes))>0 )\
                for source, target in inputoutputgraphs )
        sortkey = lambda x: ( len(x[0])-len(x[1]), len(x[0]) )
        inputoutputgraphs = sorted( inputoutputgraphs, key= sortkey)

        for sourcenodes, targetnodes in inputoutputgraphs:
            mydata = { a:b for a,b in wholegraph.items() }
            assert set(targetnodes).difference( mydata.keys() ) != set()
            if ( sourcenodes, targetnodes ) in tried_nodepairs:
                continue
            else:
                tried_nodepairs.add( (sourcenodes, targetnodes) )
            try:
                in_graph = wholegraph.subgraph( sourcenodes )
                out_graph = wholegraph.subgraph( targetnodes )
                myfoo: dg_pr.factory_leaf \
                        = comp_factleaf.gen_from_flowgraph( myflowgraph, \
                                                    in_graph, out_graph )()
                mydata = {a:b for a,b in wholegraph.items() }
                mydata = { key:value for key, value in mydata.items() \
                                                    if key in sourcenodes }
                logger.debug( f"Use nodes %s to create nodes: %s" \
                                %(str(in_graph.nodes()), \
                                set(out_graph.nodes())\
                                .difference(in_graph.nodes())) )
                asd = myfoo( **mydata )
                for key, value in asd.items():
                    wholegraph[ key ] = value
                break
            except NoPathToOutput as er:
                pass
    return wholegraph

def split_connected_subgraphs( nodes, edges ):
    edges = ( (e[0], e[1]) for e in edges if e[0] in nodes and e[1] in nodes )
    helpergraph = netx.Graph()
    for n in nodes:
        helpergraph.add_node( n )
    for e in edges:
        helpergraph.add_edge( *e )
    return netx.connected_components( helpergraph )



def create_generatordict_for_graphnodes( inout_graphnodesets, \
                                        myflowgraph, wholegraph ):
    generatable_nodes_with = dict()
    for in_graphnodes, out_graphnodes in inout_graphnodesets:
        extra_graphnodes = set( out_graphnodes ).difference( in_graphnodes )
        for single in extra_graphnodes:
            tmplist = generatable_nodes_with.setdefault( \
                            single, list() )
            tmplist.append( (in_graphnodes, out_graphnodes) )
    #sort by first maximal number of innodes and second by maximal n of outnodes
    mysort = lambda x: ( -( len(x[1])-len(x[0]) ), -len(x[0]) )
    #mysort = lambda x: ( -len(x[1]), -len(x[0]) )
    for mylist in generatable_nodes_with.values():
        mylist.sort( key = mysort )
    return generatable_nodes_with


def _complete_graph_step( generatable_nodes_with, myflowgraph, wholegraph ):
    """Generates the next possible datanodes from currentdatagraph.

    :rtype:
    """

    borderlist = wholegraph.get_completed_datanode_border( \
                                                not_completed_nodes=True)
    borderlist = list( borderlist )
    completed_nodes = set( wholegraph.get_data().keys() )
    for node in borderlist:
        for in_nodes, out_nodes in generatable_nodes_with[ node ]:
            real_innodes = set( out_nodes ).intersection( completed_nodes )
            if real_innodes.issuperset( in_nodes ):
                try:
                    in_graph = wholegraph.subgraph( real_innodes )
                    out_graph = wholegraph.subgraph( out_nodes )
                    myfoo: dg_pr.factory_leaf = comp_factleaf.create_linear_function( \
                                    myflowgraph, in_graph, out_graph )
                    mydata = wholegraph.get_data()
                    mydata = { key:value \
                                    for key, value in mydata.items() \
                                    if key in real_innodes }
                    logger.debug( f"Use nodes %s to create nodes: %s" \
                                    %(str(in_graph.nodes()), \
                                    set(out_graph.nodes())\
                                    .difference(in_graph.nodes())) )
                    asd = myfoo( **mydata )
                    return { key: value for key, value in asd.items() \
                            if key not in real_innodes }
                except NoPathToOutput as er:
                    pass
    raise Exception( f"tried to generate following nodes {borderlist}", \
                        set( wholegraph.get_data().keys() ))

def is_connected( nodes, edges ):
    testgraph = netx.Graph()
    for n in nodes:
        testgraph.add_node( n )
    for e in edges:
        testgraph.add_edge( e[0], e[1] )
    return len( list(netx.connected_components( testgraph ))) == 1

