import itertools
import logging
logger = logging.getLogger( __name__ )

class complex_targeted_factory:
    @classmethod
    def gen_from_flowgraph( cls, myflowgraph, inputgraph, outputgraph ):
        maximal_datastates =  myflowgraph.get_maximal_datastates()
        for superstate in maximal_datastates:
            pass
        #possible_outputstates = myflowgraph.find_possible_all_supergraph( \
        #                            outputgraph )


######################################
# old
#####################################

import copy
import networkx as netx
from .processes import factory_leaf, WrongDatainput
from .class_datastate import datastate
from .constants import DATAGRAPH_EDGETYPE as EDGETYPE
import math
from . import class_flowgraph as classflow
from .class_datagraph import datagraph

class FailstateReached( Exception ):
    pass
class NoPathToOutput( Exception ):
    pass
class DataRescueException( Exception ):
    """

    :ivar datagraph: ()
    """
    def __init__( self, mydatagraph, *args):
        super().__init__( *args )
        self.datagraph = mydatagraph


class complex_linear_factory_leaf( factory_leaf ):
    """
    :ivar possible_outputstates: (Dict[ datastate, Dict[Hashable, Hashable]])
            possible datastates, at which point the linearfunction returns.
            Also saves a backtranslator for used data to given outputgraph
    :ivar inputstate:
    :ivar datastate_to_process:
    :ivar inputtranslator:
    """
    def generate_datagraphs( self ):
        return self.inputgraph, self.outputgraph
    def __init__( self, inputgraph, outputgraph, datastate_to_process, \
                        possible_outputstates, inputtranslator ):
        """

        :type inputgraph: datagraph
        :type outputgraph: datagraph
        :type outputdatastate_to_translator: Dict[ datastate, \
                    Dict[Hashable,Hashable]]
        :type datastate_to_process: Dict[ datastate, Tuple[ Dict, factleaf, Dict ]]
        :param datastate_to_process: Shows which factory_leaf is to be used, 
                when certain datastate. returned tuple gives translator, 
                from saved datastate, to factleaf, the factleaf, and
                a an output to nextdatastate-translator
        :type inputtranslator: Dict[ str, str ]
        :param inputtranslator: Maps inputgraphname to inner datastatenodename
        """
        #generate_graphs = lambda: ( inputgraph, outputgraph )
        self.inputgraph = inputgraph
        self.outputgraph = outputgraph
        super().__init__()
        self.inputstate = datastate.from_datagraph( inputgraph )
        self.inputtranslator = inputtranslator

        self.datastate_to_process = datastate_to_process
        for ds, data_for_process in self.datastate_to_process.items():
            factleaf, inputtrans, outtodt_translator, \
                        generated_nodes_to_nextstate, bypass_translator\
                        = data_for_process
            for return_data, nextstate in generated_nodes_to_nextstate.items():
                assert all( q in bypass_translator.values() \
                            or q in outtodt_translator[return_data].values() \
                            for q in nextstate.get_nodetypes().keys() ), \
                            "Problem with transition between 2 states found. "

        if type( possible_outputstates ) == set:
            raise Exception( "not implemented" )
            self.possible_outputstates = possible_outputstates
        elif type( possible_outputstates ) == dict:
            self.possible_outputstates = possible_outputstates
        else:
            raise TypeError( "outputstates not correct given")

    @classmethod
    def gen_from_flowgraph( cls, myflowgraph, inputgraph, outputgraph ):
        """

        :type myflowgraph: flowgraph
        :type inputgraph: datagraph
        :type outputgraph: datagraph
        """
        raise Exception( "This function is deactivated" )
        possible_outputstates = myflowgraph.find_possible_all_supergraph( \
                                    outputgraph )
        if len( possible_outputstates ) == 0:
            raise NoPathToOutput( "Datagraph not contained in flowgraph"  )

        directionmap = myflowgraph.create_directionmap_for_output( \
                                    possible_outputstates )
        #if datastate.from_datagraph( inputgraph ) not in directionmap:
        #    raise KeyError( "cant create linear function" )
        datastate_to_process = {}
        for node, target in directionmap.items():
            processlist = myflowgraph.get_possible_processes( node, \
                                    directionmap[ node ] )
            keys, values = list( processlist.items() )[0]
            factleaf, intrans_as_keys = keys
            inputtranslation = { a:b for a,b in intrans_as_keys }
            generated_nodes_to_outtrans = {}
            generated_nodes_to_nextstate = {}
            for out_val in values:
                outputtranslation = out_val[ "outtrans" ]
                generatenodes = frozenset( out_val[ "gennode" ] )
                generated_nodes_to_outtrans[ generatenodes ] = outputtranslation
                generated_nodes_to_nextstate[ generatenodes ] = out_val[ "nextstate" ]
                bypass_translator = out_val[ "bypass_translator" ]

                assert all( q in bypass_translator.values() \
                            or q in outputtranslation.values() \
                            for q in out_val[ "nextstate" ].get_nodetypes().keys() ), \
                            str( [bypass_translator, outputtranslation, out_val[ "nextstate" ].get_nodetypes().keys()] )

            datastate_to_process[ node ] = ( \
                            factleaf, \
                            inputtranslation, \
                            generated_nodes_to_outtrans, \
                            generated_nodes_to_nextstate, \
                            bypass_translator, \
                            )
        from .class_datastate import datastate
        tmpout = datastate.from_datagraph( outputgraph )
        possible_outputstates_with_backtranslation \
                            = { st:st.find_translation_to_subset( tmpout )[0] \
                            for st in possible_outputstates }

        inputtranslator = myflowgraph.get_translator_for_datagraph( inputgraph, \
                            transtoflowgraph=True )

        if datastate.from_datagraph(inputgraph) not in datastate_to_process:
            raise NoPathToOutput( directionmap )


        return lambda: cls( inputgraph, outputgraph, datastate_to_process, \
                                    possible_outputstates_with_backtranslation,\
                                    inputtranslator )


    def call_function( self, **kwargs ):
        #assert set(kwargs.keys()) == set(self.inputstate.get_nodetypes().keys()),"wrong input"
        currentdatastate = self.inputstate
        try:
            data = { self.inputtranslator[ n ]: val for n, val in kwargs.items() }
        except KeyError as err:
            raise TypeError( "Can only accept input from %s, got %s"\
                        %( tuple(self.inputtranslator.keys()), kwargs.keys()))
        #data = dict( kwargs )
        while currentdatastate in self.datastate_to_process:
            #inputtrans, factleaf, outputtonextdatastate, \
            factleaf, inputtrans, outtodt_translator, \
                        generated_nodes_to_nextstate, bypass_translator\
                        = self.datastate_to_process[ currentdatastate ]
            logger.debug( "from datastate %s use factoryleaf %s with inputtranslation %s"%( currentdatastate, factleaf, inputtrans ))
            inputdata = { inputtrans[ n ]: datacontainer \
                        for n, datacontainer in data.items() \
                        if n in inputtrans }
            assert all( key in data for key in inputtrans ), \
                        str(("program doesnt work correct. not all inputdata is here",\
                        str( currentdatastate ), inputtrans, data.keys() ))

            outputdata = factleaf( **inputdata )

            outkey = frozenset( outputdata )
            currentdatastate = generated_nodes_to_nextstate[ outkey ]

            newdata = { t: data[s] for s, t in bypass_translator.items() }
            newdata.update({ t: inputdata[ s ] \
                        for s,t in outtodt_translator[ outkey ].items() \
                        if s in inputdata })
            newdata.update({ t: outputdata[ s ]
                        for s,t in outtodt_translator[ outkey ].items() \
                        if s in outputdata })
            logger.debug( "created data %s for next datastate %s and uses transfertranslation %s" %(newdata.keys(), currentdatastate, bypass_translator))
            olddata = data
            data = newdata
            assert all( q in currentdatastate.get_nodetypes().keys() \
                        for q in data.keys() ), "more data, than datastate "\
                        "can hold, %s, %s" %( currentdatastate.get_nodetypes()\
                        .keys(), data.keys() )
        if currentdatastate not in self.possible_outputstates:
            myerr = FailstateReached( "cant continue from this datastate on" )
            msg2 = "lastaction was: %s"%( factleaf )
            raise DataRescueException( data, olddata, msg2 ) from myerr

        returntranslator = self.possible_outputstates[ currentdatastate ]
        return { outgraph_key: data[ internal_key ]\
                for internal_key, outgraph_key in returntranslator.items() }
