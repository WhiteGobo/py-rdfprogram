import rdflib.compare as comp
import abc
import typing as typ
import networkx as netx
import itertools as it
import logging
import math
logger = logging.getLogger( __name__ )

class Edge_program( abc.ABC ):
    pass

class Program( abc.ABC ):
    @abc.abstractmethod
    def __call__( self ):
        pass
    @abc.abstractmethod
    def inputgraph( self ):
        pass
    @abc.abstractmethod
    def maximal_outputgraph( self ):
        pass


class GraphState( abc.ABC ):
    """A Graph as a state.
    """
    def __eq__( self, other ):
        if type( self ) != type( other ):
            return False
        return hash( self ) == hash( other )
    @abc.abstractmethod
    def __hash__( self ):
        pass
    @abc.abstractmethod
    def spawn_next_state_from_program( self, program: Edge_program ):
        """
        :rtype: Iterable[ GraphState ]
        """
        pass
    @abc.abstractmethod
    def spawn_prev_state_from_program( self, program: Edge_program ):
        """
        :rtype: Iterable[ GraphState ]
        """
        pass
    @abc.abstractmethod
    def spawn_starting_states_from_program( cls, program: Edge_program ):
        """Use this method as input for flowgraph.from_programs for
        parameter function_find_starstates. This method should create
        a set of possible starting states, from which the rest of the graph
        can be ascertained by usage of programs. (Just use inputgraph)

        :rtype: Iterable[ GraphState ]
        """
        pass
    @abc.abstractmethod
    def find_translation_to( self, other ) -> typ.Dict:
        pass
    #@abc.abstractmethod
    #def find_translation_to_subset( self, other ):
    #    pass

def find_superstate( programs: typ.Iterable[Program] ) -> GraphState:
    raise NotImplementedError()
    pass


FLOWGRAPH_EDGEMAP = ( GraphState, GraphState, Edge_program, 
                        typ.Dict )
"""Direction from first to second graph. Includes the program used and
a mapping of inputterms from first (input)graphstate to inputgraph of 
used program
"""

class flowgraph:
    """Directed Graph with rdfgraphs as nodes and programs as edges.
    Shows with which program you can get from one state to another.
    """
    _datacontainer: netx.MultiDiGraph
    _PROGRAM: str = "p"
    _INPUTTRANSLATION: str = "i"

    def __init__( self, states: GraphState, flowedges: FLOWGRAPH_EDGEMAP ):
        self._datacontainer = netx.MultiDiGraph()
        for source, target, program, inputtranslation in flowedges:
            try:
                self._datacontainer.add_edge( source, target, 
                                        **{self._PROGRAM: program,
                                        self._INPUTTRANSLATION: inputtranslation} )
            except Exception as err:
                raise Exception( source, target,program, self._PROGRAM ) from err

    def _get_graphstate( self ):
        return type( iter(self._datacontainer.nodes).__next__() )
    graphstate = property( fget=_get_graphstate )

    @classmethod
    def from_programs( cls, programs: typ.Iterable[Program], 
                function_find_startstates: typ.Callable[Program, typ.Iterable[GraphState]],
                limit_flowgraph_size=True,
                ):
        """Produces reachable states from programs. If a state can be 
        generated via a program from another state, this program
        cant wont be used to create new states from this state on.

        :param limit_flowgraph_size: If this parameter is set, the maximal
            number of contained states is limited to 5**number of programs

        :todo: use abbrevations for edgetypes for debugging logging
        :todo: change use of translation to use of new axioms, when creating 
            new offspring graphstates
        """
        #superstate = find_superstate( programs )
        flowedges = []
        tobevisited = []
        programs = tuple( programs )
        for p in programs:
            for x in function_find_startstates( p ):
                if x not in tobevisited:
                    tobevisited.append( x )

        statelimit = 5**len( programs )
        for currentstate in tobevisited:
            if limit_flowgraph_size:
                if len( tobevisited ) > statelimit:
                    raise TimeoutError( "Too many states found", len(tobevisited) )
            
            for p in programs:
                peek, myiter = it.tee( currentstate.spawn_prev_state_from_program(p) )
                try:
                    peek.__next__()
                    tmp_lever = True
                except StopIteration:
                    tmp_lever = False
                if tmp_lever:
                    logger.debug( "backwards node generation" )
                    for prevstate in myiter:
                        if prevstate not in tobevisited:
                            logger.debug( f"new node {prevstate}" )
                            tobevisited.append( prevstate )
                else:
                    logger.debug( "forward node generation" )
                    myiter = currentstate.spawn_next_state_from_program( p )
                    #for nextstate, new_axioms_from_currentstate in myiter:
                    for nextstate, inputtranslation in myiter:
                        flowedges.append( ( currentstate, nextstate, \
                                            p, inputtranslation ) )
                        if nextstate not in tobevisited:
                            logger.debug( f"new node {nextstate}" )
                            tobevisited.append( nextstate )


        return cls( tobevisited, flowedges )


    def create_directionmap_for_output( self, possible_endgraphs ):
        """Find mapping of states to next state to reach one state of 
        possible_endgraphs fastest.

        :type possible_endgraphs: Iterable[ GraphState ]
        :rtype: Dict[ datastate, Edge_program ]
        """
        possible_endgraphs = list( possible_endgraphs )
        paths = dict(netx.algorithms.all_pairs_shortest_path( self._datacontainer ))
        nextneighbour = {}
        toenddistance = {}
        for node in self._datacontainer.nodes:
            if node in possible_endgraphs:
                continue
            for target in possible_endgraphs:
                try:
                    mypath = paths[node][target]
                except KeyError:
                    continue
                if len( mypath ) < toenddistance.get( node, math.inf ):
                    toenddistance[ node ] = len( mypath )
                    nextneighbour[ node ] = mypath[ 1 ]
        return nextneighbour

    def get_possible_processes( self, inputstate: GraphState, 
                               outputstates: GraphState = None, 
                               neighbouring_graphstates = True ):
        """Find out which program can be used on inputstate. Can be filtered 
        by programs, that can produce outputstate.

        :param neighbouring_graphstates: If unset to False also searches 
                programs, which may lead to graphstate if this method is 
                called repeatedly. Or searches for indirect connections to 
                outputstates and returns the first programs, that can be used
        :type neighbouring_graphstates: bool
        :type target_superstates: bool
        :param target_superstates: If set will search for superstates of 
                given outputstates instead of the outputstates themselve
        :rtype: Iterable[ Dict, program ]
        :returns: list of translation of input and the program 
                useable on inputstate and producing outputstate
        :todo: asserts react first, when the generate is iterated
        """
        from networkx.algorithms import all_pairs_shortest_path
        assert type(inputstate) == type(iter(self._datacontainer).__next__())
        assert inputstate in self._datacontainer

        if outputstates is not None:
            outputstates = list(outputstates)
            assert all( x in self._datacontainer for x in outputstates ),\
                    [ x for x in outputstates if x not in self._datacontainer ]
        else:
            outputstates = []
        assert type( inputstate ) == type( iter(self._datacontainer.nodes()).__next__() )
        assert all( type( x ) == type( iter(self._datacontainer.nodes()).__next__() ) for x in outputstates )
        processes = {}

        edges = self._datacontainer.edges( data=True )
        #have to use this filter method, because networkx replaces edge[0] 
        #with given inputstate instead of the object, that is saved in graph
        edges = filter( lambda e: e[0]==inputstate, edges )
        if outputstates:
            if neighbouring_graphstates:
                edges = filter( lambda e: e[1] in outputstates, edges )
            else:
                tmp = dict(all_pairs_shortest_path( self._datacontainer ))
                is_feasible = lambda x : any( t in tmp[x] for t in outputstates )
                edges = filter( lambda e: is_feasible(e[1]), edges )
        for native_inputstate, outputstate, data in edges:
            program = data[ self._PROGRAM ]
            translation_nativestate_to_program = data[self._INPUTTRANSLATION]
            inputtranslation = _find_inputtranslation( native_inputstate, \
                                        inputstate,  \
                                        translation_nativestate_to_program )
            inputtranslation = { x:y for x,y in inputtranslation.items()
                                if y in set(program.get_inputgraph().subjects()) }
            
            yield inputtranslation, program

def _find_inputtranslation(original_inputstate, inputstate, secondtranslation):
    antifirsttranslation = original_inputstate.find_translation_to( inputstate)
    print( "abtifirsttranslation: ", antifirsttranslation )
    inputtranslation = { 
                antifirsttranslation.get(x,x): secondtranslation.get( x, x )
                for x in it.chain( antifirsttranslation , secondtranslation)
                }
    inputtranslation = { x:y for x,y in inputtranslation.items() if x!=y }
    print( inputtranslation )
    return inputtranslation

