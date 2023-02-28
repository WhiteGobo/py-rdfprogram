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

from . import Project
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
        @prefix adder: <file://adder#> .

        <{adder_uri}> a proloa:program ;
            proloa:hasArgument adder:add1, adder:add2 .
        adder:add1 proloa:id 0 ;
            rdfs:comment "loadfile" ;
            a proloa:arg ;
            proloa:describedBy _:addres1 .
        adder:add2 proloa:id 1 ;
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
        @prefix info: <file://info#> .

        <{numbertoaxiom_uri}> a proloa:program ;
            proloa:hasArgument info:ntaArg .
        info:ntaArg proloa:id 0 ;
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
    def test_project(self):
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
            @prefix info: <file://info#> .
            @prefix adder: <file://adder#> .

            #automatic generation tactic
            <file://mytactic> a autgen:tactic ;
                autgen:uses <{adder_uri}>,
                            <{numbertoaxiom_uri}> ;
                autgen:usesPriorityQueue _:adderQueue .
            _:adderQueue autgen:controls <{adder_uri}> ;
                rdfs:comment "prio = info:ntaArg->info:value" .
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


    def test_reasoning_support(self):
        g = rdflib.Graph().parse(format="ttl", data=f"""
            @prefix autgen: <http://example.com/automaticgenerator#> .
            @prefix ns1: <http://example.com/asdf#> .
            @prefix ns2: <http://swrl.stanford.edu/ontologies/3.3/swrla.owl#> .
            @prefix ns3: <http://example.com/> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix swrl: <http://www.w3.org/2003/11/swrl#> .
            @prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

            ns1:myApp ns1:proArg ns1:myResource ;
                ns3:proArg ns1:myResource ;
                proloa:executes ns1:myProgram .

            ns1:mytactic a autgen:tactic ;
                autgen:uses ns1:myProgram ;
                autgen:usesPriorityQueue _:myQueue .
            
            ns1:myProgram proloa:hasArgument ns1:proArg .
            ns1:myResource ns1:prop 3 .

            ns1:prop a owl:DatatypeProperty .
            ns3:proArg a owl:ObjectProperty .
            _:myQueue a owl:DatatypeProperty .

            <http://www.w3.org/2002/07/app> a swrl:Variable .
            <http://www.w3.org/2002/07/prio> a swrl:Variable .
            <http://www.w3.org/2002/07/res> a swrl:Variable .
            <http://www.w3.org/2002/07/val> a swrl:Variable .

            [] a swrl:Imp ;
                rdfs:label "S1"^^xsd:string ;
                ns2:isRuleEnabled true ;
                rdfs:comment ""^^xsd:string ;
                swrl:body ( [ a swrl:DatavaluedPropertyAtom ;
                            swrl:argument1 <http://www.w3.org/2002/07/res> ;
                            swrl:argument2 <http://www.w3.org/2002/07/val> ;
                            swrl:propertyPredicate ns1:prop ]
                            [ a swrl:IndividualPropertyAtom ;
                            swrl:argument1 <http://www.w3.org/2002/07/app> ;
                            swrl:argument2 <http://www.w3.org/2002/07/res> ;
                            swrl:propertyPredicate ns3:proArg ]
                            [ a swrl:BuiltinAtom ;
                            swrl:arguments ( <http://www.w3.org/2002/07/prio> <http://www.w3.org/2002/07/val> 3 ) ;
                            swrl:builtin swrlb:add ] ) ;
                swrl:head ( [ a swrl:DatavaluedPropertyAtom ;
                            swrl:argument1 <http://www.w3.org/2002/07/app> ;
                            swrl:argument2 <http://www.w3.org/2002/07/prio> ;
                            swrl:propertyPredicate _:myQueue ] ) .
        """)

        g.base = "http:/example.com/myrule#"
        node_myQueueBNode = iter(g.query("""SELECT ?x 
                            WHERE {
                                ns1:mytactic autgen:usesPriorityQueue ?x .
                            }
                            """)).__next__().x

        newaxioms = reasoning_support.reason_pellet(g)

        from rdflib import URIRef, Literal
        shouldbeaxioms = set((
                    (URIRef('http://example.com/asdf#myApp'),
                     RDF.a,
                     URIRef('http://www.w3.org/2002/07/owl#Thing')),
                    (URIRef('http://example.com/asdf#myResource'),
                     RDF.a,
                     URIRef('http://www.w3.org/2002/07/owl#Thing')),
                    (URIRef('http://example.com/asdf#mytactic'),
                     RDF.a,
                     URIRef('http://example.com/automaticgenerator#tactic')),
                    (URIRef('http://example.com/asdf#myApp'),
                     URIRef('http://example.com/proArg'),
                     URIRef('http://example.com/asdf#myResource')),
                    (URIRef('http://example.com/asdf#myApp'),
                     node_myQueueBNode,
                     Literal(6)),
                    (URIRef('http://example.com/asdf#myResource'),
                     URIRef('http://example.com/asdf#prop'),
                     Literal(3)),
                    ))
        self.assertEqual(set(newaxioms), set(shouldbeaxioms))
        owl = URIRef("http://www.w3.org/2002/07/owl#").defrag()
        newaxioms = [ax for ax in newaxioms if not any(owl in x for x in ax)]

        
if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
