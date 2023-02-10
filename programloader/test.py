import unittest
import os.path
#from . import useprogram
from . import useprogram
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
from . import evaluator
program_path = importlib.resources.files(test_src).joinpath( "myprogram.py" )
program_uri = pathlib.Path(program_path).as_uri()
evaluator_path = importlib.resources.files(test_src).joinpath("myevaluator.py")
evaluator_uri = pathlib.Path(evaluator_path).as_uri()
number_path = importlib.resources.files(test_src).joinpath("number")
number_uri = pathlib.Path(number_path).as_uri()


input_dict = {\
        PROLOA_NS.program: useprogram.create_program, \
        PROLOA_NS.mutable_resource: useprogram.mutable_resource,\
        PROLOA_NS.arg: useprogram.arg,\
        PROLOA_NS.link: useprogram.filelink,\
        PROLOA_NS.app: useprogram.app,\
        PROLOA_NS.evaluator: evaluator.evaluator.from_rdf,\
        }

class TestProgramloader( unittest.TestCase ):
    def test_evaluator(self):
        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            <{evaluator_uri}> a proloa:evaluator ;
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
        self.assertEqual( set(asdf.keys()), set(g.subjects()) )
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
                              ])
        print("\n\n")
        print(g.serialize(format="n3"))
        self.assertEqual(set(new_axioms), shouldbeaxioms)

    def test_simple( self ):
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
            _:2 proloa:describedBy _:res2 .
            _:res2 a proloa:mutable_resource ;
                asdf:customProp2 asdf:customResource2 .
            _:res2 asdf:customProp3 _:res1 .
        """)
        asdf: dict = rl.load_from_graph( useprogram.input_dict, g )
        self.assertEqual( set(asdf.keys()), set(g.subjects()) )

        app_iri = URIRef("http://example.com/meinBefehl")
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
        myfilelink: useprogram.filelink = asdf[linkid][0]
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


if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
