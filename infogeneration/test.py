import unittest
import rdflib
import logging
logger = logging.getLogger( __name__ )
from . import tactic
from . import AUTGEN
import rdfloader as rl
import programloader

import importlib.resources
import pathlib
import os.path
from . import test_src
adder_path = importlib.resources.files(test_src).joinpath( "adder.py" )
adder_uri = pathlib.Path(program_path).as_uri()

input_dictionary = {
        AUTGEN.tactic: tactic.tactic,
        }
input_dictionary.update(programloader.input_dict)

class TestInfogenerator( unittest.TestCase ):
    def test_simple(self):
        g = rdflib.Graph().parse(format="ttl", data=f"""
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix asdf: <http://example.com/> .
            @prefix autgen: <http://example.com/automaticgenerator#> .

            #automatic generation tactic
            <file://mytactic> a autgen:tactic ;
                autgen:uses <file://path/to/adder>,
                            <file://path/to/numbertoaxiom> .

            #Program number 1
            <{adder_uri}> a proloa:program ;
                proloa:hasArgument _:add1, _:add2 .
            _:add1 proloa:id 0 ;
                rdfs:comment "loadfile" ;
                a proloa:arg ;
                proloa:describedBy _:addres1 .
            _:add2 proloa:id 1 ;
                rdfs:comment "savefile" ;
                a proloa:arg ;
                proloa:describedBy _:addres2 .

            _:addres1 a proloa:mutable_resource ;
                a asdf:number .
            _:addres2 a proloa:mutable_resource ;
                a asdf:number .
            _:addres1 asdf:greater _:addres2 .

            #Program number 2
            <file://path/to/numbertoaxiom> a proloa:program ;
                proloa:hasArgument _:ntaArg .
            _:ntaArg proloa:id 0 ;
                rdfs:comment "loadfile" ;
                a proloa:arg ;
                proloa:describedBy _:ntaRes .
            _:ntaRes a proloa:mutable_resource ;
                a asdf:number .
            """)
        generated_objects = rl.load_from_graph(input_dictionary, g)
        raise Exception(generated_objects)
        
if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
