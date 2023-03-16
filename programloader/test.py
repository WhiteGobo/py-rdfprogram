import unittest
import os.path
from . import Program
import rdfloader as rl
import logging
logger = logging.getLogger( __name__ )
import rdflib
import rdflib.compare
from rdflib import URIRef
import importlib.resources
import tempfile

import pathlib
import os.path
from . import test_src
from . import PROLOA_NS
from . import RDF_NS
program_path = importlib.resources.files(test_src).joinpath( "myprogram.py" )
program_uri = rdflib.URIRef(pathlib.Path(program_path).as_uri())
evaluator_path = importlib.resources.files(test_src).joinpath("myevaluator.py")
evaluator_uri = rdflib.URIRef(pathlib.Path(evaluator_path).as_uri())
number_path = importlib.resources.files(test_src).joinpath("number")
number_uri = pathlib.Path(number_path).as_uri()
notnumber_path = importlib.resources.files(test_src).joinpath("notnumber")
notnumber_uri = pathlib.Path(notnumber_path).as_uri()

from . import Arg
from . import Filelink
from . import App

input_dict = {\
        PROLOA_NS.program: Program.rdfprogram.from_rdf, \
        PROLOA_NS.arg: Arg.arg,\
        PROLOA_NS.link: Filelink.filelink,\
        PROLOA_NS.app: App.app,\
        }

class TestProgramloader( unittest.TestCase ):
    def test_search_in_graphs_for_possible_app(self):
        """Testing if programs have full support to return graphs equivalent to
        input and output. Also tests if program can succesfully search in
        a given graph for needed input
        """
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            # This is the description of the program
            <{program_uri}> a proloa:program ;
                proloa:hasArgument _:1, _:2 .
            _:1 proloa:id 0 ;
                a proloa:arg .
            _:2 proloa:id "--savefile" ;
                a proloa:arg .

            # This is a description what the programs needs as argument 
            # and what the result of the program looks like
            _:1 proloa:describedBy _:res1 .
            _:res1 a proloa:mutable_resource ;
                asdf:customProp1 asdf:customResource1 .
            #_:2 proloa:describedBy _:res2 .
            _:2 proloa:declaresInfoLike _:res2 .
            _:res2 a proloa:mutable_resource ;
                asdf:customProp2 asdf:customResource2 .
            _:res2 asdf:customProp3 _:res1 .
            """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        try:
            myprogram: "program" = asdf[program_uri][0]
        except Exception as err:
            raise Exception("couldnt load. See other tests.") from err
        arg_input, arg_output = iter(g.query(f"""SELECT ?e ?g
            WHERE {{
                <{program_uri}> proloa:hasArgument ?e, ?g .
                ?e proloa:describedBy [] .
                ?g proloa:declaresInfoLike [] .
            }}""")).__next__()
        myprogram.var_to_argid
        #shouldbesearch = set(myprogram.old_axioms)
        shouldbesearch = set([(arg_input, rdflib.URIRef('http://example.com/customProp1'), rdflib.URIRef('http://example.com/customResource1'))])
        q = myprogram.var_to_argid
        inputaxioms = {tuple(q[x] if x in q else x 
                             for x in ax) for ax in myprogram.inputgraph}
        self.assertEqual(inputaxioms, shouldbesearch, "searchgraph was wrong.")
        #shouldbewhole = set(myprogram.new_axioms)
        shouldbewhole = set([
            #(mutnode_example, rdflib.URIRef('http://example.com/customProp1'), rdflib.URIRef('http://example.com/customResource1')),
            (arg_output, rdflib.term.URIRef('http://example.com/customProp2'), rdflib.term.URIRef('http://example.com/customResource2')), 
            (arg_output, rdflib.term.URIRef('http://example.com/customProp3'), arg_input),
            ])
        outputaxioms = {tuple(q.get(x,x) for x in ax)
                        for ax in myprogram.outputgraphs[0]}
        self.assertEqual(outputaxioms, shouldbewhole, "outputgraphs is wrong")
        self.assertEqual(len(myprogram.outputgraphs),1,"too many outputgraphs")

        target_g = rdflib.Graph().parse(format="ttl", data="""
            @prefix asdf: <http://example.com/> .
            asdf:1 asdf:customProp1 asdf:customResource1 .
            """)
        q = list(myprogram.search_in(target_g))
        self.assertEqual(len(q), 1, "failed to find inputgraph.")
        inputvar = iter(x for x,y in myprogram.var_to_argid.items()
                        if y==arg_input).__next__()
        self.assertEqual(q[0], 
                         {inputvar: rdflib.URIRef("http://example.com/1")})
        e2 = myprogram.create_possible_apps(target_g)
        raise Exception(e2)


    def test_failing_evaluator(self):
        """Testing what happens if an evaluator fails, when applied to
        a list of resources. There must be a returned axiom that specifies,
        that the evaluator fails on given input
        """
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            <{evaluator_uri}> a proloa:program ;
                proloa:hasArgument _:1 .
            _:1 proloa:id 0;
                rdfs:comment "loadfile" ;
                a proloa:arg ;
                proloa:describedBy [a proloa:mutable_resource];
                proloa:declaresInfoLike _:generatedNode.

            _:generatedNode a proloa:mutable_resource;
                asdf:customProp1 asdf:customResource1 .

            asdf:meinBefehl proloa:executes <{evaluator_uri}> ;
                a proloa:app ;
                _:1 <{notnumber_uri}>.
            <{notnumber_uri}> a proloa:link .
        """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        #self.assertEqual( set(asdf.keys()), set(g.subjects()) ) #bnodes are not loaded
        appuri = URIRef("http://example.com/meinBefehl")
        myapp = asdf[appuri][0]
        returnstring, new_axioms = myapp()
        logger.debug("returnstring in test_failing_evaluator:\n%s"%(returnstring))
        expected_axioms = {(appuri, RDF_NS.a, PROLOA_NS.failedApp)}
        self.assertEqual(set(new_axioms), expected_axioms)


    def test_evaluator(self):
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            <{evaluator_uri}> a proloa:program ;
                proloa:hasArgument _:1 .
            _:1 proloa:id 0;
                rdfs:comment "loadfile" ;
                a proloa:arg ;
                proloa:describedBy [a proloa:mutable_resource];
                proloa:declaresInfoLike _:generatedNode.

            _:generatedNode a proloa:mutable_resource;
                asdf:customProp1 asdf:customResource1 .

            asdf:meinBefehl proloa:executes <{evaluator_uri}> ;
                a proloa:app ;
                _:1 <{number_uri}>.
            <{number_uri}> a proloa:link .

        """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        #self.assertEqual( set(asdf.keys()), set(g.subjects()) ) #bnodes are not loaded
        myapp = asdf[URIRef("http://example.com/meinBefehl")][0]
        returnstring, new_axioms = myapp()

        asdf_customProp1 = URIRef("http://example.com/customProp1")
        asdf_customResource1 = URIRef("http://example.com/customResource1")
        linkid = iter(g.query("""
            SELECT ?x
            WHERE {
                <http://example.com/meinBefehl> ?y ?x .
                ?y proloa:id 0 .
            }""")).__next__()[0]
        shouldbeaxioms = set([ 
                              (linkid, asdf_customProp1, asdf_customResource1),
                              (linkid,rdflib.URIRef("http://example.com/containsNumber"),rdflib.Literal(3))
                              ])
        self.assertEqual(set(new_axioms), shouldbeaxioms, returnstring)

        myprogram = asdf[evaluator_uri][0]
        self.assertEqual(myprogram.app_args[0].id, 0)
        ex_node = myprogram.app_args[0].example_node
        ge_node = myprogram.app_args[0].generated_node
        self.assertEqual(myprogram.old_axioms, [])
        asdf_customProp1 = URIRef("http://example.com/customProp1")
        asdf_customResource1 = URIRef("http://example.com/customResource1")
        self.assertEqual(set(myprogram.new_axioms), 
                         {(ge_node, asdf_customProp1, asdf_customResource1)})

    def test_failed_program(self):
        """Testing what happens if a program fails. It loads a program 
        then tries to execute it with an invalid input, namely a str
        instead of an int
        """
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            # This is the description of the program
            <{program_uri}> a proloa:program ;
                proloa:hasArgument _:1, _:2 .
            _:1 proloa:id 0 ;
                a proloa:arg .
            _:2 proloa:id "--savefile" ;
                a proloa:arg .

            # This is the description, how the program should be executed
            asdf:meinBefehl proloa:executes <{program_uri}> ;
                a proloa:app ;
                _:1 "ein string" .

            # This is a description what the programs needs as argument 
            # and what the result of the program looks like
            _:1 proloa:describedBy _:res1 .
            _:res1 a proloa:mutable_resource ;
                asdf:customProp1 asdf:customResource1 .
            #_:2 proloa:describedBy _:res2 .
            _:2 proloa:declaresInfoLike _:res2 .
            _:res2 a proloa:mutable_resource ;
                asdf:customProp2 asdf:customResource2 .
            _:res2 asdf:customProp3 _:res1 .
        """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        #self.assertEqual( set(asdf.keys()), set(g.subjects()) ) #bnodes are not loaded

        app_iri = URIRef("http://example.com/meinBefehl")
        returnstring, new_axioms = asdf[ app_iri ][0]()

        logger.debug("returnstring in test_failing_evaluator:\n%s"%(returnstring))
        expected_axioms = {(app_iri, RDF_NS.a, PROLOA_NS.failedApp)}
        self.assertEqual(set(new_axioms), expected_axioms)

    def test_get_information(self):
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            # This is the description of the program
            <{program_uri}> a proloa:program ;
                proloa:hasArgument _:1, _:2 .
            _:1 proloa:id 0 ;
                a proloa:arg .
            _:2 proloa:id "--savefile" ;
                a proloa:arg .

            # This is the description, how the program should be executed
            asdf:meinBefehl proloa:executes <{program_uri}> ;
                a proloa:app ;
                _:1 2 ;
                _:2 [a proloa:link].

            # This is a description what the programs needs as argument 
            # and what the result of the program looks like
            _:1 proloa:describedBy _:res1 .
            _:res1 a proloa:mutable_resource ;
                asdf:customProp1 asdf:customResource1 .
            #_:2 proloa:describedBy _:res2 .
            _:2 proloa:declaresInfoLike _:res2 .
            _:res2 a proloa:mutable_resource ;
                asdf:customProp2 asdf:customResource2 .
            _:res2 asdf:customProp3 _:res1 .
            _:res1 asdf:customProp3 _:res2 .
        """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        #self.assertEqual( set(asdf.keys()), set(g.subjects()) ) #bnodes are not loaded

        app_iri = URIRef("http://example.com/meinBefehl")
        #myApp = asdf[ app_iri ][0]
        myProgram = asdf[program_uri][0]

        #dont need extra test. later tests sufficient
        myProgram.example_nodes 
        myProgram.generated_nodes

        for arg in myProgram.app_args:
            if arg.id == 0:
                ex_node = arg.example_node
            elif arg.id == "--savefile":
                ge_node = arg.generated_node
            else:
                raise Exception("unexpected argument", arg, arg.id )
        asdf_customProp1 = URIRef("http://example.com/customProp1")
        asdf_customProp2 = URIRef("http://example.com/customProp2")
        asdf_customProp3 = URIRef("http://example.com/customProp3")
        asdf_customResource1 = URIRef("http://example.com/customResource1")
        asdf_customResource2 = URIRef("http://example.com/customResource2")
        ex_axioms = {
                (ex_node, asdf_customProp1, asdf_customResource1),
                }
        ge_axioms = {
                (ge_node, asdf_customProp2, asdf_customResource2),
                (ge_node, asdf_customProp3, ex_node),
                (ex_node, asdf_customProp3, ge_node),
                }
        self.assertEqual(ex_axioms, set(myProgram.old_axioms), 
                         msg=f"additional info: oldnode: {ex_node} "
                         f"new node: {ge_node}")
        self.assertEqual(ge_axioms, set(myProgram.new_axioms),
                         msg=f"additional info: oldnode: {ex_node} "
                         f"new node: {ge_node}")


    def test_simple( self ):
        """Tests if algorithm can load a program and can execute it,
        as sepcifided in an 'app'. The program is specified via RDF.

        Description of the program:
        Executes a program that adds 3 to the given number
        and can save it in file 'savefile' if given.
        """
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            # This is the description of the program
            # adds 3 to given number and saves it in savefile
            <{program_uri}> a proloa:program ;
                proloa:hasArgument _:1, _:2 .
            _:1 proloa:id 0 ;
                a proloa:arg .
            _:2 proloa:id "--savefile" ;
                a proloa:arg .

            # This is the description, how the program should be executed
            asdf:meinBefehl proloa:executes <{program_uri}> ;
                a proloa:app ;
                _:1 2 ;
                _:2 [a proloa:link].

            # This is a description what the programs needs as argument 
            # and what the result of the program looks like
            _:1 proloa:describedBy _:res1 .
            _:res1 a proloa:mutable_resource ;
                asdf:customProp1 asdf:customResource1 .
            #_:2 proloa:describedBy _:res2 .
            _:2 proloa:declaresInfoLike _:res2 .
            _:res2 a proloa:mutable_resource ;
                asdf:customProp2 asdf:customResource2 .
            _:res2 asdf:customProp3 _:res1 .
        """)
        asdf: dict = rl.load_from_graph( input_dict, g )
        #self.assertEqual( set(asdf.keys()), set(g.subjects()) ) #bnodes are not loaded

        app_iri = URIRef("http://example.com/meinBefehl")
        myapp = asdf[ app_iri ][0]
        returnstring, new_axioms = asdf[ app_iri ][0]()
        #returnstring is determined by executed program. In this example
        #it just prints out the sum of the given number and 3
        self.assertEqual(int(returnstring), 2+3)

        linkid = iter(g.query("""
            SELECT ?x
            WHERE {
                <http://example.com/meinBefehl> ?y ?x .
                ?y proloa:id "--savefile" .
            }""")).__next__()[0]
        myfilelink: Filelink.filelink = asdf[linkid][0]
        with open( myfilelink.filepath, "r" ) as f:
            saved_number = int( "".join(f.readlines()) )
        self.assertEqual(int(saved_number), 2+3, 
                         msg="filepath from filelink wasnt given to program")

        meinBefehl = asdf[ URIRef("http://example.com/meinBefehl") ][0]
        self.assertEqual({x.id: y for x, y in meinBefehl.input_args.items()},
                         {0: 2, '--savefile': myfilelink})

        asdf_customProp1 = URIRef("http://example.com/customProp1")
        asdf_customProp2 = URIRef("http://example.com/customProp2")
        asdf_customProp3 = URIRef("http://example.com/customProp3")
        asdf_customResource1 = URIRef("http://example.com/customResource1")
        asdf_customResource2 = URIRef("http://example.com/customResource2")
        shouldbeaxioms = set([ 
                              (linkid, asdf_customProp2, asdf_customResource2),
                              (linkid, asdf_customProp3, rdflib.Literal(2)),
                              ])
        self.assertEqual(set(new_axioms), shouldbeaxioms)

        #test if application recognizes, that it was already applied
        for ax in new_axioms:
            g.add(ax)
        #asdf[ app_iri ][0].was_already_executed(g)


if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
