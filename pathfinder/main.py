from .. import useprogram
from .. import rdf_loader as rl
import rdflib
import rdflib.compare
import networkx as netx
import itertools as it

State = rdflib.compare.IsomorphicGraph
Edge = str #howtouse_program


Base_automaton = "http://program/automaton#%s"
URI_auto_basicfactory = Base_automaton %( "complex_program_linearfactory" )
URI_auto_factorypart = Base_automaton %( "factorypart" )
URI_auto_executable = Base_automaton %( "executable" )
URI_auto_generates = rdflib.term.URIRef( Base_automaton %( "generates" ) )
URI_auto_generatabledata = rdflib.term.URIRef( Base_automaton %( "generatabledata" ) )


URI_auto_output = Base_automaton %( "output" )
URI_auto_uses = Base_automaton %( "uses" )
URI_auto_executes = Base_automaton %( "executes" )


class factory_graph:
    def __init__( self, url, ontology_organizer, \
            used_programs: rl.info_attr( URI_auto_factorypart, is_iter=True ),\
            ):
        if not all( hasattr(x,"get_inputgraph") for x in used_programs ):
            raise TypeError("get_inputgraph is missing")
        if not all( hasattr(x,"get_outputgraph") for x in used_programs ):
            raise TypeError("get_outputgraph is missing")
        self.used_programs = used_programs

    def __call__( self ):
        print("-"*60)
        print( self.used_programs )
        print( [ x.uri for x in self.used_programs ] )
        flowgraph.from_programcontainers( self.used_programs )
        raise Exception( "qwe" )


class factoryleaf:
    prestatus: netx.Graph
    poststatus: netx.Graph
    @classmethod
    def from_program_container( cls, program_container ):
        prestatus = program_container.get_inputgraph()
        poststatus = program_container.get_outputgraph()
        variables: list[ rdflib.URIRef ] = [ x.generates.uri \
                                for x in program_container.attributes ]
        simple_in_graph = rdf_simplification_graph( prestatus, variables )
        simple_out_graph = rdf_simplification_graph( poststatus, variables )

        return cls( simple_in_graph, simple_out_graph )

    def __init__( self, prestatus, poststatus ):
        """
        :type prestatus: rdf_simplification_graph
        :param prestatus: input used for command. Usage of graph_simplification,
                see rdf_simplification_graph for more information.
        :type poststatus: rdf_simplification_graph
        :param poststatus: maximal output for command. Usage of 
                graph_simplification, see rdf_simplification_graph for 
                more information.
        """
        self.prestatus = prestatus
        self.poststatus = poststatus


    def __call__( self, **args ):
        raise Exception()
        try:
            return self.call_function( **args )
        except TypeError as err:
            import inspect
            q = inspect.signature( self.call_function )
            if all( key in q.parameters.keys() for key in args) \
                    and all( key in args for key,p in q.parameters.items() \
                    if inspect._empty == p.default ):
                raise err #typeerror was raised within call_function
            function_reference = ".".join((self.call_function.__module__, \
                                            self.call_function.__name__ ))
            errmessage = "definition of call function doesnt work with "\
                        "definition of inputdatagraph. inputdatagraph gives "\
                        "input: %s and call_function is defined with: %s" \
                        %( args.keys(), function_reference ) 
            raise WrongDatainput( errmessage ) from err

    def nodename_to_datatype( self ):
        raise Exception()
        """Return a dictionary that maps the innernodenames to the used 
        datatype

        :rtype: Dict[ Hashable, datatype ]
        """
        datatype_dict = self.prestatus.get_node_datatypes()
        datatype_dict.update( self.poststatus.get_node_datatypes() )
        return datatype_dict


    def get_possible_addnodes( self ):
        raise Exception()
        """Get nodes, which are removed, during factoryleaf process.
        The nodes are removed, which are in prestatus, but not in poststatus.

        :rtype: Tuple[ Hashable,... ]
        :returns: All nodes, which are removed during factleaf-call
        """
        possible_add_nodes = tuple(( n \
                        for n in self.poststatus.get_node_datatypes() \
                        if n not in self.prestatus.get_node_datatypes() ))
        return possible_add_nodes

    def get_removenodes( self, translator=None ):
        raise Exception()
        """Get nodes, which are removed, during factoryleaf process.
        The nodes are removed, which are in prestatus, but not in poststatus.

        :rtype: Tuple[ Hashable,... ]
        :returns: All nodes, which are removed during factleaf-call
        """
        if translator is None:
            remove_nodes = tuple(( n \
                        for n in self.prestatus.get_node_datatypes() \
                        if n not in self.poststatus.get_node_datatypes() ))
        else:
            remove_nodes = tuple(( translator[ n ] \
                        for n in self.prestatus.get_node_datatypes() \
                        if n not in self.poststatus.get_node_datatypes() ))
        return remove_nodes

    def get_removeedges( self, translator=None ):
        raise Exception()
        """Get nodes connected to removenodes( see get_removenodes ).

        :rtype: List[ Tuple[ Hashable, Hashable, edgetype ]]
        :returns: All edges, which are removed during factleaf-call
        """
        remove_nodes = self.get_removenodes()
        if translator is None:
            remove_edges = [ (v1, v2, etype) \
                            for v1, v2, etype in self.prestatus.edges() \
                            if any((v in remove_nodes for v in (v1, v2))) ]
        else:
            remove_edges = [ (translator[v1], translator[v2], etype) \
                            for v1, v2, etype in self.prestatus.edges() \
                            if any((v in remove_nodes for v in (v1, v2))) ]
        return remove_edges

    def get_addedges_to_node( self, addnode, translator=None, filternodelist=None ):
        raise Exception()
        """

        :param filternodelist: edges with only nodes contained here. if
                translator is used, trnaslated nodesare to be used
                (translator.values()) as nodes
        :rtype: Iterable[ Tuple[ Hashable, Hashable, edgetype]]
        """
        if translator is None:
            newedges = [ (v1, v2, etype) \
                        for v1, v2, etype in self.poststatus.edges() \
                        if any( v == addnode for v in (v1, v2) ) ]
        else:
            newedges = [ (translator[v1], translator[v2], etype) \
                        for v1, v2, etype in self.poststatus.edges() \
                        if any( v == addnode for v in (v1, v2) ) ]
        if filternodelist is not None:
            myfilter = set( filternodelist).union( (addnode,) )
            newedges = [ (v1, v2, etype) \
                        for v1, v2, etype in newedges \
                        if all( v in myfilter for v in (v1, v2) ) ]
        return newedges



class ComplexNotValidInput( Exception ):
    """Thrown when attempting to use program with complex, which has no valid 
    inputparameters
    """
    pass

class flowgraph:
    @classmethod
    def from_programcontainers( cls, used_programs ):
        """

        :type used_programs: : useprogram.program_container
        """
        all_factleafs = [ factoryleaf.from_program_container(x) for x in used_programs ]

        

        raise Exception( "brubru" )
        startgraphs: State = get_start_complexes()
        nodecontainer = list( startgraphs )
        edges = []

        for x in nodecontainer:
            for f in factoryleafs:
                try:
                    generator_edges: Iterator[(Edge, State)] = cls.generate_edges( x, f )
                except ComplexNotValidInput:
                    continue
                for e, y in generator_edges:
                    if y not in newgraphs:
                        nodecontainer.append( y )
                    edges.append( ( x, e, y ) )

        return
        asd = rl.load( useprogram.uri_to_class, rdf_resource )
        programs = filter( it.chain.from_iterable(asd.values()), \
                            key=lambda x:type(x)==program_container )

    @classmethod
    def generate_edges( cls, state, factoryleaf ):
        """

        :raises: ComplexNotValidInput
        """
        get_input_translator
        possible_new_axioms = get_output_data

        edge = howtouse_factoryleaf
        
        asd = get_combinations( possible_new_axioms )
        for x in asd:
            new_complex = state + x
            for comp in cls._limit_complex_size( new_complex ):
                yield edge, comp

    @classmethod
    def _limit_complex_size( cls, state, extra_infos ):
        """Splits complex in parts so that a maximum number of rdf:type 
        is hold

        :returns: Iterator[ State ]
        """
        pass
        

    @classmethod
    def from_factory_leafs( cls, factory_leaf_list, conclusion_leaf_list=[] ):
        """

        :todo: use abbrevations for edgetypes for debugging logging
        """
        factory_leaf_list = [ l() for l in factory_leaf_list ]
        datatype_to_maxnumber = get_datanode_maximal_occurence( factory_leaf_list )
        i = 0
        node_to_datatype = {}
        for datatype, maxnumb in datatype_to_maxnumber.items():
            for j in range( maxnumb ):
                node_to_datatype[ f"d{i}" ] = datatype
                i += 1
        logger.debug( f"Uses datacontainer for flowgraph: {node_to_datatype}" )
        edgeabbrevations = find_abbrevations_for_edgetypes( factory_leaf_list, \
                                                        conclusion_leaf_list )
        logger.debug( f"used abbrevations for edgetypes: {edgeabbrevations}" )
        
        #somesomething with the conclusions
        factleaf_information = get_userequirement_for_factoryleafs( \
                                        factory_leaf_list, node_to_datatype )
        logger.debug( f"Requirements for each factoryleaf {factleaf_information}" )

        mystates = list( set( datastate.from_datagraph( factleaf.prestatus,\
                            nodenamelist_with_datatype=node_to_datatype )\
                            for factleaf in factory_leaf_list ) )
        if len(conclusion_leaf_list) != 0:
            mystates = list( state.spawn_new_datastate_from_conclusionleafs( \
                                conclusion_leaf_list ) for state in mystates )
        logger.debug( f"starting datastates: %s" \
                    %( ", ".join( i.__str__(edgeabbrevations) for i in mystates ) ))
        tobevisited = list( mystates )
        assert len(set( mystates )) == len( mystates )
        flowedges = list()
        """Edges which show, how to get from dt to dt per factleaf"""
        for currentstate in tobevisited:
            logger.debug( f"Find edges from datastate {currentstate}" )
            info_generator = find_useable_factleafs( currentstate, \
                                            node_to_datatype, \
                                            factleaf_information )
            def nextstep( factleaf, inputtranslations, possible_add_nodes, \
                                            factleafname_to_datatype, \
                                            dt_to_available_nodes ):
                for trans in inputtranslations:
                    logger.debug( f"find newnodes for factoryleaf{factleaf} "\
                                    f"operate on {trans}" )
                    newinfo = find_possible_newnodes( trans, possible_add_nodes,\
                                    factleafname_to_datatype, \
                                    dt_to_available_nodes )
                    for newnodes, factleaf_to_datastate in newinfo:
                        yield newnodes, factleaf, factleaf_to_datastate, trans
            info_generator2 = it.chain.from_iterable( nextstep(*i) \
                                    for i in info_generator )

            for newnodes, factleaf, factleaf_to_datastate, factleafinputtrans \
                                                            in info_generator2:
                logger.debug( f"Use newnodes %s " \
                        %( {i:factleaf_to_datastate[i] for i in newnodes}))

                nextdatastate, outputtrans, newnodes, trans_current_to_next \
                        = _create_edge_in_flowgraph( newnodes, factleaf, \
                                    factleaf_to_datastate, currentstate, \
                                    node_to_datatype, factleafinputtrans, \
                                    mystates, tobevisited )
                assert set( trans_current_to_next.values() )\
                                .union( outputtrans.values())\
                                == set( nextdatastate.get_nodetypes().keys() ), 1

                nextdatastate = nextdatastate\
                        .spawn_new_datastate_from_conclusionleafs( \
                                    conclusion_leaf_list )

                assert set( trans_current_to_next.values() )\
                                .union( outputtrans.values())\
                                == set( nextdatastate.get_nodetypes().keys() ), 2

                try:
                    tmpindex = mystates.index( nextdatastate )
                    extratrans = nextdatastate.find_translation_to( \
                                                        mystates[ tmpindex ] )
                    trans_current_to_next = { key: extratrans[ val ] \
                                for key, val in trans_current_to_next.items() }
                    outputtrans = { key: extratrans[ val ] \
                                for key, val in outputtrans.items() }
                    nextdatastate = mystates[ tmpindex ]
                except ValueError: #nextdatastate not in list
                    pass
                assert set( trans_current_to_next.values() )\
                                .union( outputtrans.values())\
                                == set( nextdatastate.get_nodetypes().keys() ), 3


                logger.debug( "Found edge to ds %s" \
                                %( nextdatastate.__str__(edgeabbrevations)) )
                if nextdatastate not in mystates:
                    logger.debug( "added datastate as new datastate" )
                    assert len(get_insulas( nextdatastate ))==1, (factleaf, currentstate.get_nodetypes(), currentstate.get_edges_with_edgetype(), nextdatastate.get_nodetypes(), nextdatastate.get_edges_with_edgetype() )
                    mystates.append( nextdatastate )
                    tobevisited.append( nextdatastate )
                else:
                    tmpindex = mystates.index( nextdatastate )
                    saved_nextdatastate = mystates[ tmpindex ]
                    assert set(nextdatastate.get_nodetypes().keys() )\
                            == saved_nextdatastate.get_nodetypes().keys(), "wjy"

                assert set( trans_current_to_next.values() )\
                                .union( outputtrans.values())\
                                == set( nextdatastate.get_nodetypes().keys() ), 4
                tmpindex = mystates.index( currentstate )
                assert currentstate.get_nodetypes().keys() ==mystates[ tmpindex ].get_nodetypes().keys()
                tmpindex = mystates.index( nextdatastate )
                assert nextdatastate.get_nodetypes().keys() ==mystates[ tmpindex ].get_nodetypes().keys()


                data = { "factory_leaf":factleaf, \
                                    "inputtranslation": factleafinputtrans,\
                                    "outputtranslation": outputtrans,\
                                    "generated_nodes": newnodes,\
                                    "bypass_translator": trans_current_to_next ,\
                                    }
                flowedges.append( (currentstate, nextdatastate, data) )
        return cls( node_to_datatype, mystates, flowedges )

class program_container_with_graphs( useprogram.program_container ):
    def __init__( self, uri, ontology_organizer, \
                attributes: rl.info_attr( URI_auto_uses, is_iter=True ), \
                out_attributes: rl.info_attr( URI_auto_output, is_iter=True ), \
                executes_program: rl.info_attr( URI_auto_executes ) = None, \
                ):
        """

        :todo: changed attributes and out_attributes to pre_init input as hotfix.
                should be later reversed. If it isnt important
        """
        super().__init__( uri, ontology_organizer, attributes, out_attributes, executes_program )

    def get_inputgraph( self ):
        """Calculates the minimal inputinformation graph for this command to use
        """
        try:
            return self._inputgraph
        except AttributeError:
            self._find_inout_graph()
            return self._inputgraph
    def get_outputgraph( self ):
        """Calculates the maximal information, that can exist, after this
        command was used
        """
        try:
            return self._outputgraph
        except AttributeError:
            self._find_inout_graph()
            return self._outputgraph
                
    def _find_inout_graph( self ):
        """

        :todo: transfer names from ontology.organizer.rdfgraph
        :todo: change rdflib.Graph generation with use of bind_namespace, 
                when rdflib becomes to version 6.2
        """
        out_attributes = [ x for x in self.out_attributes
                        if x.generates ]
        in_attributes = [ x for x in self.attributes \
                        if x not in self.out_attributes
                        and x.generates ]
        print( "next attributes: there should be something listed there" )
        print( self.out_attributes )
        print( self.attributes )
        print( "filtered attributes: " )
        print( in_attributes )
        print( out_attributes )
        in_placeholders = []
        for x in in_attributes:
            try:
                in_placeholders.append( x.generates )
            except AttributeError:
                pass
        out_placeholders = []
        for x in out_attributes:
            try:
                out_placeholders.append( x.generates )
            except AttributeError:
                pass
        inputgraph = rdflib.Graph( #bind_namespaces="rdflib",
                                    base=self.ontology_organizer.rdfgraph.base)
        outputgraph = rdflib.Graph( #bind_namespaces="rdflib",
                                    base=self.ontology_organizer.rdfgraph.base)
        for prefix, namespace in self.ontology_organizer.rdfgraph.namespaces():
            inputgraph.namespace_manager.bind( prefix, namespace )
            outputgraph.namespace_manager.bind( prefix, namespace )
        in_urls = [ rdflib.term.URIRef( x.uri ) for x in in_placeholders ]
        out_urls = in_urls \
                    + [ rdflib.term.URIRef( x.uri ) for x in out_placeholders ]
        for x in in_urls:
            for _,b,c in it.chain( 
                    self.ontology_organizer.rdfgraph.triples(( x, None, None )),\
                    self.ontology_organizer.rdfgraph.triples(( None, None, x ))):
                if b == URI_auto_generates:
                    continue
                inputgraph.add( (x,b,c) )
                outputgraph.add( (x,b,c) )
        for x in out_urls:
            for _,b,c in it.chain( 
                    self.ontology_organizer.rdfgraph.triples(( x, None, None )),\
                    self.ontology_organizer.rdfgraph.triples(( None, None, x ))):
                if b == URI_auto_generates:
                    continue
                #if c == URI_auto_generatabledata:
                #    continue
                outputgraph.add( (x,b,c) )

        self._inputgraph = inputgraph
        self._outputgraph = outputgraph

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
        self.data = netx.Graph()
        super().__init__()
        nodenames = [ rdflib.term.URIRef( x ) for x in nodenames ]
        to_B = rdflib.BNode
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

    def get_data_for_nodes( self, nodenames: list[ str ] ) -> rdflib.Graph :
        datagraph = rdflib.Graph()
        nodenames = [ rdflib.term.URIRef( x ) for x in nodenames ]
        sg = self.data.subgraph( nodenames )
        for n, data in it.chain( sg.nodes( data=True ), sg.edges(data=True) ):
            for axiom in data[ self._RDFINFO ]:
                datagraph.add( axiom )
        return datagraph

    def get_variables( self ):
        return self.data.nodes()




        


uri_to_class = { \
        URI_auto_basicfactory: factory_graph, \
        URI_auto_executable: program_container_with_graphs, \
        }
