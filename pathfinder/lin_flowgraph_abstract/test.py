import unittest
from ._flowgraph import flowgraph
from . import _graphstate as graphstate
from . import create_program_from_datagraph
import rdflib
import rdflib.term
import rdflib.compare as comp
import logging
logger = logging.getLogger( __name__ )
import typing as typ
import itertools as it


from dataclasses import dataclass
@dataclass
class ip( graphstate.information_placeholder ):
    uri: rdflib.term.Identifier

@dataclass
class attr( graphstate.program_attribute ):
    generates: ip

class test_p( graphstate.program ):
    attributes: typ.Iterable[ attr ]
    def __init__( self, pre, post, name="" ):
        self.name = str(name)
        self.variables = { x
                    for x in it.chain(pre.subjects(), post.subjects())
                    if type(x) == rdflib.BNode }
        self.attributes = []
        for x in self.variables:
            self.attributes.append( attr(ip(x)) )
        self.pre = pre
        self.post = post
    def get_inputgraph( self ):
        return self.pre
    def get_outputgraph( self ):
        return self.post
    def get_inputstate( self ):
        graph = comp.to_isomorphic( self.pre )
        return graphstate.graphstate( graph, rename=False )
    def get_outputstate( self ):
        graph = comp.to_isomorphic( self.post )
        return graphstate.graphstate( graph, rename=False )
    def __str__( self ):
        return "<program: %s>"%( self.name )


class test_flowgraph( unittest.TestCase ):

    def test_graphstate( self ):
        """This just tests the normal behaviour of rdflib.
        """
        from rdflib.term import BNode, URIRef

        type_of = URIRef( "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" )
        ex = URIRef( "http://example.com/mytype" )
        edge = URIRef( "http://example.com/edge" )
        pre1 = rdflib.Graph()
        pre1.add( (BNode("a"), type_of, ex) )
        post1 = rdflib.Graph()
        post1.add( (BNode("a"), type_of, ex) )
        post1.add( (BNode("a"), edge, BNode("b")) )
        post1.add( (BNode("b"), type_of, ex) )
        post2 = rdflib.Graph()
        post2.add( (BNode("a"), type_of, ex) )
        post2.add( (BNode("a"), edge, BNode("b")) )
        post2.add( (BNode("b"), type_of, ex) )
        from rdflib.compare import to_isomorphic
        self.assertEqual( to_isomorphic(post1), to_isomorphic(post2), msg ="test method isnt correctly implemented" )
        #self.assertEqual( to_isomorphic(post1).vhash(), to_isomorphic(post2).vhash(), msg ="test method isnt correctly implemented" )

        g1 = graphstate.graphstate( post1 )
        g2 = graphstate.graphstate( post2 )
        self.assertEqual( g1.rdfgraph, g2.rdfgraph )
        self.assertEqual( g1, g2 )
        self.assertEqual( hash(g1), hash(g2) )

    def test_graphstate_to_sparql( self ):
        """Tests, if a sparql search can be constructed via a graphstate
        """
        post1 = rdflib.Graph().parse( format="ttl", data="""
                @prefix ex: <http://example.com/> .
                @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
                _:a a ex:mytype .
                _:b a ex:mytype .
                _:a ex:edge _:b .
                """ )
        posttest = rdflib.Graph().parse( format="ttl", data="""
                @prefix ex: <http://example.com/> .
                @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
                @prefix t: <test://t/> .
                t:1 a ex:mytype .
                t:2 a ex:mytype .
                t:1 ex:edge t:2 .
                """ )
        test_res1 = rdflib.URIRef("test://t/1")
        test_res2 = rdflib.URIRef("test://t/2")

        g1 = graphstate.graphstate_to_sparql_search( post1 )
        all_found = list( g1.search_in( posttest ) )
        self.assertEqual( len(all_found), 1 )
        self.assertEqual( set(all_found[0].values()), {test_res1, test_res2 } )
        antitrans = { b:a for a,b in all_found[0].items() }
        all_found = list( g1.search_in( posttest, \
                        {antitrans[ test_res1 ]: test_res1 }) )
        self.assertEqual( len(all_found), 1 )
        self.assertEqual( set(all_found[0].values()), { test_res2 } )


    type_of = rdflib.URIRef( "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" )
    ex = rdflib.URIRef( "http://example.com/mytype" )
    ex2 = rdflib.URIRef( "http://example.com/mytype2" )
    ex3 = rdflib.URIRef( "http://example.com/mytype3" )
    edge = rdflib.URIRef( "http://example.com/edge" )
    edge2 = rdflib.URIRef( "http://example.com/edge2" )

    pre1 = rdflib.Graph()
    pre1.add( (rdflib.BNode("a"), type_of, ex) )
    post1 = rdflib.Graph()
    post1.add( (rdflib.BNode("a"), type_of, ex) )
    post1.add( (rdflib.BNode("a"), edge, rdflib.BNode("b")) )
    post1.add( (rdflib.BNode("b"), type_of, ex) )
    testprogram = test_p( pre1, post1, 1 )


    pre3 = rdflib.Graph()
    pre3.add( (rdflib.BNode("a"), type_of, ex) )
    post3 = rdflib.Graph()
    post3.add( (rdflib.BNode("a"), type_of, ex) )
    post3.add( (rdflib.BNode("a"), edge, rdflib.BNode("b")) )
    post3.add( (rdflib.BNode("b"), type_of, ex3) )
    testprogram3 = test_p( pre3, post3, 3 )

    prepre2 = rdflib.Graph()
    prepre2.add( (rdflib.BNode("a"), type_of, ex) )
    prepre2.add( (rdflib.BNode("a"), type_of, ex2) )
    pre2 = rdflib.Graph()
    pre2.add( (rdflib.BNode("a"), type_of, ex) )
    pre2.add( (rdflib.BNode("a"), type_of, ex2) )
    pre2.add( (rdflib.BNode("a"), edge, rdflib.BNode("b")) )
    pre2.add( (rdflib.BNode("b"), type_of, ex) )
    post2 = rdflib.Graph()
    post2.add( (rdflib.BNode("a"), type_of, ex) )
    post2.add( (rdflib.BNode("a"), type_of, ex2) )
    post2.add( (rdflib.BNode("a"), edge, rdflib.BNode("b")) )
    post2.add( (rdflib.BNode("b"), type_of, ex) )
    post2.add( (rdflib.BNode("a"), edge2, rdflib.BNode("c")) )
    post2.add( (rdflib.BNode("c"), type_of, ex) )
    testprogram2 = test_p( pre2, post2, 2 )


    def test_flowgraph_forward_graphstates( self ):
        """In a flowgraph, you can find which program can be used
        to find the next graphstate. The next graphstate can be given.
        Tests if the commands can be ascertained by the flowgraph.
        Also finds out if the correct translation of the given state
        and the inputstate of the program.
        Tests if flowgraph creation, generates gaphstates, by ascertaining, 
        which graphstates can be reached from a graphstate with given program
        """
        from dataclasses import dataclass
        from rdflib.term import BNode, URIRef

        type_of = URIRef( "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" )
        ex = URIRef( "http://example.com/mytype" )
        edge = URIRef( "http://example.com/edge" )
        myflow = flowgraph.from_programs( [ self.testprogram ], graphstate.graphstate.spawn_starting_states_from_program )
        self.assertTrue( 0 < len( myflow._datacontainer.nodes() ), msg="flowgraph is empty. No graphstates could be ascertained" )
        q = myflow.create_directionmap_for_output( [graphstate.graphstate(self.post1)] )
        startstate = graphstate.graphstate( self.pre1 )
        endstate = graphstate.graphstate( self.post1 )
        self.assertTrue( startstate in q.keys(), msg="flowgraph doesnt include prestatus of given program" )
        self.assertTrue( endstate in q.values(), msg="flowgrapgh has no way to solution of program" )

        with self.subTest( "transition from one state in flowgraph" ):
            logger.debug( "subtest: find program in flowgraph 1" )
            a = myflow.get_possible_processes( startstate )
            a = tuple(a)
            tmp_map, tmp_program = a[0]
            self.assertEqual( len(a), 1 )
            self.assertEqual( tmp_program, self.testprogram )
            self.assertEqual( {}, tmp_map,
                             msg="returned mapping isnt what i expected" )
        with self.subTest( "transition from one homomorph state" ):
            logger.debug( "subtest: find program in flowgraph 2" )
            pre2 = rdflib.Graph()
            pre2.add( (BNode("c"), type_of, ex) )
            startstate2 = graphstate.graphstate( pre2 )
            c = myflow.get_possible_processes( startstate2 )
            c = tuple(c)
            tmp_map, tmp_program = c[0]
            self.assertEqual( len(c), 1 )
            self.assertEqual( self.testprogram, tmp_program )
            self.assertEqual( {BNode("c"):BNode("a")}, tmp_map, \
                            msg="returned mapping isnt what i expected" )

        with self.subTest( "find program between states in flowgraph" ):
            logger.debug( "subtest: find program in flowgraph 3" )
            a = myflow.get_possible_processes( startstate, [endstate] )
            a = tuple(a)
            tmp_map, tmp_program = a[0]
            self.assertEqual( len(a), 1 )
            self.assertEqual( self.testprogram, tmp_program )
            self.assertEqual( {}, tmp_map, \
                            msg="returned mapping isnt what i expected" )

        #self.subtest_flowgraph_backwards_spawn()

        with self.subTest("No nodes will be removed in any process"):
            logger.debug( "subtest:No nodes will be removed in any process" )
            myflow2 = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate_onlynodes.spawn_starting_states_from_program )
            wholegraph = rdflib.Graph()\
                        .parse( data = src_teststate_small_nodechain )
            tmp_state = graphstate.graphstate_onlynodes( wholegraph )
            for tmp_map, tmp_program in myflow2.get_possible_processes( \
                                                            tmp_state ):
                self.assertEqual( len(tmp_map), 1, msg="Only 1 inputnode required"+str(tmp_map) )


        with self.subTest( "Test if nameconfliction will be solved" ):
            logger.debug( "subtest: test if nameconfliction" )
            myflow2 = flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate.spawn_starting_states_from_program )
            tmp_graph = rdflib.Graph()
            tmp_graph.add( (BNode("c"), self.type_of, self.ex ) )
            tmp_graph.add( (BNode("c"), self.edge, BNode("d") ) )
            tmp_graph.add( (BNode("d"), self.type_of, self.ex ) )
            tmp_state = graphstate.graphstate( tmp_graph )
            tmp_all_nodes = list( tmp_state.rdfgraph.all_nodes() )
            for tmp_map, tmp_program in myflow2.get_possible_processes( \
                                                            tmp_state ):
                self.assertTrue( all( o in tmp_map.keys() 
                                     or o not in tmp_all_nodes
                                     for o in tmp_map.values() ),
                                msg = "after mapping a nameconfliction exists"\
                                        +f"mapping: {tmp_map}" \
                                        +f"all_nodes: {tmp_all_nodes}" \
                                )
                self.assertEqual( tmp_program, self.testprogram3,\
                        msg="wrong program was used at this point" )


    def test_flowgraph_backwards_spawn( self ):
        """Tests if flowgraph and graphstates, can produce graphstates, \
        which are predecessors to certain graphstates constructed by program
        """
        myflow = flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram2 ], \
                        graphstate.graphstate.spawn_starting_states_from_program )
        self.assertTrue( 0 < len( myflow._datacontainer.nodes() ), \
                        msg="flowgraph is empty. No graphstates "\
                        "could be ascertained" )
        q = myflow.create_directionmap_for_output( \
                        [graphstate.graphstate(self.post2)] )
        teststate1 = graphstate.graphstate( self.prepre2 )
        teststate2 = graphstate.graphstate( self.pre2 )
        teststate3 = graphstate.graphstate( self.post2 )
        for idtag, source, target in ( \
                        ("preinput", teststate1, teststate2), \
                        ("input", teststate2, teststate3), \
                        ):
            with self.subTest( f"used idtag '{idtag}'" ):
                self.assertTrue( source in q, msg="missing input key" )
                self.assertEqual( q[source], target, msg="wrong output" )

    def test_graphstate_onlynodes( self ):
        """Tests the subclass graphstate_onlynodes
        """
        myflow2 = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate_onlynodes.spawn_starting_states_from_program )
        states = myflow2._datacontainer.nodes()
        for s in states:
            #print( s.get_nodetype_to_nodes() )
            pass

    def test_create_simple_linear_creation( self ):
        """Tests if flowgraph can ascertain, which programs have to be used
        to generate a graphstate from another graphstate.
        Both graphstates are in this case inside the flowgraph.
        To generate the output-graphstate multiple programs have to be used.
        """
        myflow = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate.spawn_starting_states_from_program )

        startstate = graphstate.graphstate( rdflib.Graph().parse( data= src_teststate_simplenode ) )
        endstate = graphstate.graphstate( rdflib.Graph().parse( data= src_teststate_nodechain ) )
        smallstate = graphstate.graphstate( rdflib.Graph().parse( data= src_teststate_small_type3 ) )

        with self.subTest( "if neighbouring_graphstat failing" ):
            a = myflow.get_possible_processes( startstate, [endstate], \
                                                neighbouring_graphstates=True )
            self.assertEqual( len(tuple(a)), 0, msg="states should not be neighbouring and so here no program should be found." )

        with self.subTest( "if not neighbouring_graphstat succeeding" ):
            a = myflow.get_possible_processes( startstate, [endstate], 
                                                neighbouring_graphstates=False )
            a = tuple( a )
            self.assertEqual( len(a), 1, msg="states should be indirectly connected so here usable programs should be found" )
            tmp_map, tmp_program = a[0]
            self.assertEqual( self.testprogram, tmp_program )
            #self.assertEqual( {BNode("something") : BNode("a")}, tmp_map, \
            #                    msg="returned mapping isnt what i expected" )
        with self.subTest( "if not targeting_substates failing to search" ):
            self.assertRaises( AssertionError, 
                              lambda: tuple( myflow.get_possible_processes( 
                                        startstate, [smallstate], 
                                        neighbouring_graphstates=False ) )
                              )

        myflow2 = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate_onlynodes.spawn_starting_states_from_program )
        smallstate_onlynodes = graphstate.graphstate_onlynodes( smallstate.rdfgraph )
        startstate_onlynodes = graphstate.graphstate_onlynodes( startstate.rdfgraph )

        with self.subTest( "if targeting_substates succeeding to search" ):

            superstates = tuple( myflow2.find_superstates_to( smallstate_onlynodes ) )
            self.assertEqual( 3, len( superstates) )
            a = myflow2.get_possible_processes( startstate_onlynodes, superstates, 
                                            neighbouring_graphstates=False )
            a = tuple( a )
            self.assertEqual( len(a), 2, msg="states should be indirectly connected so here usable programs should be found" )
            #tmp_map, tmp_program = a[0]
            #self.assertEqual( self.testprogram, tmp_program )
            #self.assertEqual( {BNode("something") : BNode("a")}, tmp_map, \
            #                    msg="returned mapping isnt what i expected" )

    #@unittest.expectedFailure
    @unittest.skip( "first get subtest no nodes will be removed right" )
    def test_complex_linear_datafactory( self ):
        """Tests if flowgraph can how a graphstate can be produced.
        The given graphstate is in this test not a a subgraph of one graph
        in the flowgraph. But to every node a substate of the given
        graphstate must be inside of the flowgraph.
        """
        myflow2 = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate_onlynodes.spawn_starting_states_from_program )
        wholegraph = rdflib.Graph()
        wholegraph.parse( publicID="asdf", data = src_test_complex_linear_datafactory )
        #logger.debug( wholegraph.serialize(format="nt") )
        print( wholegraph.serialize(format="nt") )
        self.assertEqual( len(list(myflow2._get_nodetypes())), 2 )
        self.assertTrue( len(list(myflow2._datacontainer)) \
                        > len(list(myflow2._get_superstates())) )

        BASE_URI_auto = "http://program/automaton#"
        URI_typeof = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        URI_generation_target = rdflib.URIRef( f"{BASE_URI_auto}generation_target" )
        filtered_wholegraph = rdflib.Graph()
        for a,b,c in wholegraph:
            if not (b == URI_typeof and c == URI_generation_target):
                filtered_wholegraph.add( (a,b,c) )
        
        qwer = myflow2.find_partgraphs( filtered_wholegraph )
        q = myflow2._get_generators_to()
        mini = list( myflow2._find_minimal_generating_graphstates() )
        self.assertEqual( 1, len(list( myflow2._find_minimal_generating_graphstates())))
        #create_program_from_datagraph.complete_datagraph( myflow2, wholegraph )
        #input_outputgraphs, missing_nodes, filtered_wholegraph = myflow2.complete_datagraph( wholegraph,  )
        #self.assertEqual( len(input_outputgraphs), 8 )
        #self.assertEqual( len(missing_nodes), 2 )
        #filtered_wholegraph
        myiter = test_program_iterator.from_flowgraph( myflow2, wholegraph )
        list( myiter )

class test_program_iterator( create_program_from_datagraph.program_iterator ):
    def execute_program( self, graphstate, input_translation, program ):
        print( "execute" )
        print( "input trans: ", input_translation )
        print( program )
        transfer_nodes = [x for x in graphstate.mutable_resources \
                            if x not in input_translation ]
        print( "transfer nodes: ", transfer_nodes )
        anti_trans = { b:a for a,b in input_translation.items() }
        outgraph = program.get_outputgraph()
        print( outgraph.serialize() )
        ingraph = program.get_inputgraph()
        print( ingraph.serialize() )
        trans_outgraph = rdflib.Graph()
        #import uuid
        #my_id = uuid.uuid4()

        for a,b,c in outgraph:
            trans_outgraph.add( (anti_trans.get(a,a),b, anti_trans.get(c,c)) )
        print( input_translation, anti_trans )
        ret = type( graphstate )( trans_outgraph )
        print( "new nodes: ", ret.mutable_resources )
        return ret
        return trans_outgraph

src_teststate_simplenode = """
[] a <http://example.com/mytype> .
"""

src_teststate_small_nodechain = """
@prefix ns1: <http://example.com/> .

[] a ns1:mytype ;
    ns1:edge [ a ns1:mytype ].
"""

src_teststate_nodechain = """
@prefix ns1: <http://example.com/> .

[] a ns1:mytype ;
    ns1:edge [ a ns1:mytype ;
            ns1:edge [ a ns1:mytype3 ] ] .
"""

src_teststate_small_type3 = """
@prefix ns1: <http://example.com/> .

[] a ns1:mytype3 .
"""


src_test_complex_linear_datafactory = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix example: <http://example.com/> . 
@prefix auto: <http://program/automaton#> .

_:a a example:mytype .
_:b a example:mytype, auto:generation_target .
_:c a example:mytype, auto:generation_target .
_:a example:edge _:b .
_:b example:edge _:c .
"""

if __name__ == "__main__":
    #logging.basicConfig( level=logging.DEBUG )
    unittest.main()
