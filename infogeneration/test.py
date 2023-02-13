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
mypath_prefix = pathlib.Path(importlib.resources.files(test_src)).as_uri() + "/"
adder_path = importlib.resources.files(test_src).joinpath( "adder.py" )
adder_uri = pathlib.Path(adder_path).as_uri()
numbertoaxiom_path = importlib.resources.files(test_src).joinpath( "numbertoaxiom.py" )
numbertoaxiom_uri = pathlib.Path(numbertoaxiom_path).as_uri()

input_dictionary = {
        AUTGEN.tactic: tactic.tactic,
        }
input_dictionary.update(programloader.input_dict)

info_adder_uri = f"""@prefix asdf: <http://example.com/> .
        @prefix proloa: <http://example.com/programloader/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix testpath: <{mypath_prefix}> .

        <{adder_uri}> a proloa:program ;
            proloa:hasArgument _:add1, _:add2 .
        _:add1 proloa:id 0 ;
            rdfs:comment "loadfile" ;
            a proloa:arg ;
            proloa:describedBy _:addres1 .
        _:add2 proloa:id 1 ;
            rdfs:comment "savefile" ;
            a proloa:arg ;
            proloa:declaresInfoLike _:addres2 .

        _:addres1 a proloa:mutable_resource ;
            a asdf:number .
        _:addres2 a proloa:mutable_resource ;
            a asdf:number .
        _:addres1 asdf:greater _:addres2 .
"""

info_numbertoaxiom = f"""@prefix asdf: <http://example.com/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix proloa: <http://example.com/programloader/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix testpath: <{mypath_prefix}> .

        <{numbertoaxiom_uri}> a proloa:program ;
            proloa:hasArgument _:ntaArg .
        _:ntaArg proloa:id 0 ;
            rdfs:comment "loadfile" ;
            a proloa:arg ;
            proloa:declaresInfoLike _:ntaNew ;
            proloa:describedBy _:ntaRes .
        _:ntaRes a proloa:mutable_resource ;
            a asdf:number .
        _:ntaNew a proloa:mutable_resource ;
            a asdf:checkednumber .
"""

class TestInfogenerator( unittest.TestCase ):
    def test_simple(self):
        g = rdflib.Graph().parse(format="ttl", data=f"""
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix autgen: <http://example.com/automaticgenerator#> .
            @prefix testpath: <{mypath_prefix}> .

            #automatic generation tactic
            <file://mytactic> a autgen:tactic ;
                autgen:uses <{adder_uri}>,
                            <{numbertoaxiom_uri}> .
            """)
        g.parse(data = info_numbertoaxiom)
        g.parse(data = info_adder_uri)
        generated_objects = rl.load_from_graph(input_dictionary, g)
        self.assertEqual(set(generated_objects), set(g.subjects()))

        mytactic = generated_objects[rdflib.URIRef("file://mytactic")][0]

        fileuri =rdflib.URIRef("file://asdf")
        infograph = rdflib.Graph().parse(format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            <{fileuri}> a asdf:number .
            """)
        asdf = mytactic.get_priorities(infograph)
        expected_axioms = {(fileuri, AUTGEN.priority, rdflib.Literal(0.0))}
        self.assertEqual(set(asdf), expected_axioms)
        
if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
