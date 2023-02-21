import unittest
import rdflib
import logging
logger = logging.getLogger( __name__ )
from . import tactic
from . import AUTGEN
from programloader import RDF_NS as RDF
from programloader import PROLOA_NS as PROLOA
import rdfloader as rl
import programloader
import queue

from . import reasoning_support
import importlib.resources
import pathlib
import os.path
from . import test_src
mypath_prefix = pathlib.Path(importlib.resources.files(test_src)).as_uri() + "/"
adder_path = importlib.resources.files(test_src).joinpath( "adder.py" )
adder_uri = rdflib.URIRef(pathlib.Path(adder_path).as_uri())
numbertoaxiom_path = importlib.resources.files(test_src).joinpath( "numbertoaxiom.py" )
numbertoaxiom_uri = rdflib.URIRef(pathlib.Path(numbertoaxiom_path).as_uri())
testnumber_path = importlib.resources.files(test_src).joinpath( "a_number" )
testnumber_uri = rdflib.URIRef(pathlib.Path(testnumber_path).as_uri())

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
    def test_reasoning_support(self):
        g = rdflib.Graph().parse(format="ttl", data=f"""
            @base <http:/example.com/myrule#> .
            @prefix autgen: <http://example.com/automaticgenerator#> .
            @prefix ns1: <http:/example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix swrl: <http://www.w3.org/2003/11/swrl#> .
            @prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            ns1:myApp proloa:executes ns1:myProgram ;
                ns1:proArg ns1:myResource .

            ns1:mytactic a autgen:tactic ;
                autgen:uses ns1:myProgram ;
                autgen:usesPriorityQueue ns1:myQueue .

            ns1:myResource ns1:prop 3 .
            ns1:myProgram proloa:hasArgument ns1:proArg .

            <app> a swrl:Variable .
            <val> a swrl:Variable .
            <prio> a swrl:Variable .

            [] a swrl:Imp ;
                rdfs:comment "prop(?res, ?val) proArg(?app ?res) swrlb:add(?prio, ?val, 3) -> myQueue(?app, ?prio)" ;
                swrl:body ( [ a swrl:BuiltinAtom ;
                            swrl:arguments ( <prio> <val> 3 ) ;
                            swrl:builtin swrlb:add ] ) ;
                swrl:head ( [ a swrl:IndividualPropertyAtom ;
                            swrl:argument1 <app> ;
                            swrl:argument2 <prio> ;
                            swrl:propertyPredicate <myQueue> ] ) .""")
        g.base = "http:/example.com/myrule#"

        for x in reasoning_support.reason_update(g):
            raise Exception(x)
            pass


    @unittest.skip("asdf")
    def test_simple(self):
        """
        
        :TODO: remake priority. It should be some kind of property bound
            to the tactic.
        """
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

        infograph = rdflib.Graph().parse(format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            <{testnumber_uri}> a asdf:number ;
                a proloa:link .
            """)
        asdf = mytactic.get_priorities(infograph)
        app_resources = [s for s,p,o in asdf if p==RDF.a and o==PROLOA.app]
        self.assertEqual(len(app_resources), 1, msg="There should be exactly "
                                f"one BNode here: {app_resources}")
        res_app = app_resources[0]
        arg_resource = iter(g.query(f"""
            SELECT ?x
            WHERE {{
                <{numbertoaxiom_uri}> proloa:hasArgument ?x .
                ?x proloa:id 0 .
            }}""")).__next__()[0]
        expected_axioms = {
                (res_app, RDF.a, PROLOA.app),
                (res_app, PROLOA.executes, numbertoaxiom_uri),
                (res_app, AUTGEN.priority, rdflib.Literal(0.0)),
                (res_app, arg_resource, testnumber_uri),
                (arg_resource, RDF.a, PROLOA.arg),
                }
        self.assertEqual(set(asdf), expected_axioms)

        returnstring, new_axioms = mytactic.execute_first_app()
        self.assertRaises(queue.Empty, mytactic.execute_first_app)
        raise Exception(returnstring, new_axioms)
        
if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
