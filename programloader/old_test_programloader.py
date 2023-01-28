import unittest
import os.path
from . import useprogram
import rdfloader as rl
import logging
logger = logging.getLogger( __name__ )
import rdflib
import rdflib.compare
import importlib.resources
import tempfile
import itertools as it
try:
    import owlready2 as owl
except ModuleNotFoundError:
    owl = None

class TestProgramLoader( unittest.TestCase ):
    def setUp( self ):
        """

        :todo: Maybe this is better worked out with pathlib
        """
        self.rootpath, _ = os.path.split( os.path.abspath( __file__ ) )
        self.test_path = os.path.join( self.rootpath, "test_src", "" )
        self.program_path = os.path.join( self.test_path, "myprogram.py" )
        self.program_url = "file://" + self.program_path
        self.test_path_url = "file://" + self.test_path
        self.assertTrue( os.path.exists( self.program_path ), msg=f"testfiles not found, {self.program_path}" )


    def test_simple( self, firstint=5, secondint=13 ):
        """Executes prgram myprogram.py from testdirectory. For this
        it loads that program via rdfloader, calls the program_container
        and then checks, if the return value is correct and if the
        file, where the data is saved, has the correct data in it
        """
        #tmpfile = tempfile.TemporaryFile
        #tmpfileurl = "file://" + os.abspath( tmpfile.path )

        rdf_resource = f"""@base <{self.test_path_url}> .
                    @prefix auto: <http://program/automaton#> .
                    @prefix testsrc: <{self.test_path_url}>.
                    <myprogram.py> a auto:executable .
                    <myprogram.py> auto:uses <1>, <2>, <3>.
                    <1> a auto:argument .
                    <1> auto:index 0 .
                    <1> auto:default {firstint} .
                    <2> a auto:argument .
                    #<2> auto:index 1 .
                    <2> auto:default {secondint} .
                    <2> auto:keyword '--secint' .
                    <3> a auto:argument .
                    #<3> auto:index 2 .
                    #<3> auto:default <file.data> .
                    <3> auto:keyword '--savefile' .
                    <file.data> a auto:data .
                """
        g = rdflib.Graph().parse( data=rdf_resource )
        asd = rl.load_from_graph( useprogram.rdfnode_to_class, g )

        #asd = rl.ontology_organizer.load( useprogram.uri_to_class, rdf_resource ).to_dict()

        #tores = lambda x: os.path.join( self.test_path_url, x )
        #self.assertEqual( set(asd.keys()), 
        #                    { self.program_url, tores("1"), 
        #                    tores("2"), tores("3"), tores("file.data") } )
        #self.assertIn( self.program_url, asd )
        program = filter( lambda x: type(x)==useprogram.program_container, \
                    asd[rdflib.URIRef( self.program_url )] ).__next__()
        ret, newresources = program()
        #ret, newresources = program( skip_reasoning=True )
        self.assertEqual( int(ret), firstint + secondint )

        with tempfile.NamedTemporaryFile() as tmpfile:
            tmpurl = "file://%s" %( tmpfile.name )

            extra_resources = "\n".join(( f"@base <{self.test_path_url}> . ", \
                        f"@prefix root: <{self.test_path_url}> . ", \
                        f"@prefix auto: <http://program/automaton#> . ", \
                        f"<mycommand> a auto:command . ", \
                        f"<mycommand> auto:executes root:myprogram.py . ", \
                        f"<mycommand> auto:uses [ a auto:argument ; auto:default <{tmpurl}> ; auto:overwrite root:3 ] . ", \
                        f"<{tmpurl}> a auto:data .", \
                        ))
            command_uri = self.test_path_url + "mycommand"
            asd2 = rl.ontology_organizer.load( useprogram.uri_to_class, rdf_resource, extra_resources ).to_dict()
            self.assertIn( command_uri, asd2 )
            program = filter( lambda x: type(x)==useprogram.program_container, \
                        asd2[command_uri] ).__next__()
            ret, newresources = program( skip_reasoning=True )
            with tmpfile as q:
                saved_number = int( b"".join(q) )
            self.assertEqual( saved_number, firstint + secondint )

    @unittest.skip( "old" )
    def test_newinformation_generation( self, firstint=3, secondint=42):
        rdf_resource ="\n".join( [ f"@base <{self.test_path_url}> . ", \
                        f"@prefix auto: <http://program/automaton#> . ", \
                        f"@prefix help: <http://example.com/> . ", \
                        f"@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",\
                        f"@prefix owl: <http://www.w3.org/2002/07/owl#> .", \
                        f"<myprogram.py> a auto:executable . ", \
                        f"<myprogram.py> auto:uses <1>, <2>, <3>. ", \
                        f"<1> a auto:argument . ", \
                        f"<1> auto:index 0 .", \
                        f"<1> auto:default {firstint} .", \
                        f"<2> a auto:argument . ", \
                        #f"<2> auto:index 1 .", \
                        f"<2> auto:default {secondint} .", \
                        f"<2> auto:keyword '--secint' . ", \
                        f"<3> a auto:argument . ", \
                        f"<3> a owl:Thing . ", \
                        #f"<3> auto:index 2 .", \
                        #f"<3> auto:default <file.data> .", \
                        f"<3> auto:keyword '--savefile' . ", \
                        f"<3> auto:generates <qq> . ", \
                        f"<qq> a auto:generatabledata .", \
                        f"<qq> a help:sum .", \

                        f"<myprogram.py> auto:uses <4>. ", \
                        f"<4> a auto:argument . ", \
                        f"<4> a owl:Thing . ", \
                        f"<4> auto:keyword '--placeholder' . ", \
                        f"<4> auto:generates <qq2> . ", \
                        f"<qq2> a auto:generatabledata .", \
                        f"<http://example.com/my#property> a owl:ObjectProperty .",\
                        f"<qq> <http://example.com/my#property> <qq2>.", \
                        #f"<http://example.com/my#property> a rdf:Property.", \
                        ] )
        with self.subTest( "add created status to rdfgraph" ):
            self.subtest_newrdf_data_through_program( firstint, secondint, rdf_resource )
        with self.subTest( "transport axioms from placeholder to created things"):
            if owl:
                self.subtest_transfer_placeholder_information( firstint, secondint, rdf_resource )
            else:
                raise Exception( "owlready2 not available. no logic possible" )


    def subtest_newrdf_data_through_program( self, firstint, secondint, rdf_resource ):
        """We need to create a temporary file for our new information, 
        so that the algorithm can save the solution and create for 
        the new resource the information.
        Test if the method useprogram.interpolate_newinformation 
        labels, the new resource via auto:created

        :todo: handle problems, with multiple default_target problem
        """
        #create information, that should in reality be available as file
        #rdf_resource = self.create_program_information( firstint, secondint )
        with tempfile.NamedTemporaryFile() as tmpfile:
            tmpurl = "file://%s" %( tmpfile.name )
            logger.debug( f"{tmpurl} is the created resource, by the program" )
            mycommand = "mycommand"
            extra_resources = "\n".join(( f"@base <{self.test_path_url}> . ", \
                        f"@prefix root: <{self.test_path_url}> . ", \
                        f"@prefix auto: <http://program/automaton#> . ", \
                        f"<{mycommand}> a auto:command . ", \
                        f"<{mycommand}> auto:executes root:myprogram.py . ", \
                        f"<{mycommand}> auto:uses <qq>.",\
                        #"[ a auto:argument ; ",\
                        #f"auto:default <{tmpurl}> ; ",\
                        #f"auto:default_target <{tmpurl}> ; ",\
                        #f"auto:overwrite root:3 ] . ", \
                        f"<qq> a auto:argument . ",\
                        f"<qq> auto:default <{tmpurl}> . ",\
                        f"<qq> auto:default_target <{tmpurl}> . ",\
                        f"<qq> auto:overwrite root:3 . ", \
                        f"<{tmpurl}> a auto:data .", \
                        ))
            command_uri = self.test_path_url + mycommand

            asd2 = rl.ontology_organizer.load( useprogram.uri_to_class, rdf_resource, \
                                                extra_resources )
            self.assertIn( command_uri, asd2.to_dict() )
            program = filter( lambda x: type(x)==useprogram.program_container,\
                        asd2.to_dict()[command_uri] ).__next__()
            old_axioms = list( asd2.rdfgraph )
            ret, newresources = program( skip_reasoning=True )
            new_axioms = list( asd2.rdfgraph )
            self.assertEqual( int(ret), firstint + secondint )
            with open( tmpfile.name, "r" ) as targetfile:
                self.assertEqual( [str(firstint + secondint)], \
                                                targetfile.readlines() )

        #Dont need this anymore interpolate will be done inside command.__call__
        #new_axioms = useprogram.interpolate_newinformation( newresources, \
        #                                        rdf_resource, extra_resources )
        new_axioms = [ x for x in new_axioms if x not in old_axioms ]

        ref = lambda x: rdflib.term.URIRef( x )
        expected_new_axioms = [
                (ref( self.test_path_url + "qq" ),
                ref("http://program/automaton#created"),
                ref( tmpurl )),
                #(ref( tmpurl ), \
                #ref('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), \
                #ref('http://example.com/sum')),\
                ]
        expected = set( " ".join(x) for x in expected_new_axioms )
        new = set( " ".join(x) for x in new_axioms )

        #self.assertEqual( expected_new_axioms, new_axioms, msg="Tests the"\
        self.assertEqual( expected, new, msg="First expected axioms, second "\
                "are the generated axioms by the algo. If there is "\
                "axiom with 'qq2' as subject, the algorithm failed to "\
                "differentiate between placeholders and new resources." )

    def subtest_transfer_placeholder_information( self, firstint, secondint, rdf_resource,\
                                                debug=0 ):
        """Tries to transfer all data hold, by resource placeholder, 
        towards the new generated resource.
        The resource itself, will not created here, but instead it will
        just be declared as created by statement 'attr auto:created new'.

        :todo: currently reasoning doesnt work reliable, if anonymous 
            resources are used. Therefore if this problem is resolved with
            owlready2, the resources should be made anonymous as far as
            it is reasonable
        """

        created_resources : str
        """These RDF-resources will be created by 
        useprogram.interpolate_newinformation
        """

        #rdf_resource = self.create_program_information( firstint, secondint )
        with tempfile.NamedTemporaryFile() as command_target:
            tmpurl = "file://%s" %( command_target.name )

            mycommand = "mycommand"
            extra_resources = "\n".join(( f"@base <{self.test_path_url}> . ", \
                        f"@prefix root: <{self.test_path_url}> . ", \
                        f"@prefix auto: <http://program/automaton#> . ", \
                        f"@prefix owl: <http://www.w3.org/2002/07/owl#> . ",\
                        #f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.",\
                        f"<{mycommand}> a auto:command . ", \
                        f"<{mycommand}> auto:executes root:myprogram.py . ", \
                        #f"<{mycommand}> auto:uses <asdf> .",\
                        #f"<asdf> a auto:argument ; auto:default <{tmpurl}> ; auto:default_target <{tmpurl}> ; auto:overwrite root:3 . ", \
                        f"<{mycommand}> auto:uses <abc3> .",\
                        f"<abc3> a auto:argument ; auto:default <{tmpurl}> ; auto:default_target <{tmpurl}> ; auto:overwrite root:3 .", \
                        #f"<{mycommand}> auto:uses [ a auto:argument ; auto:default <abc2_target> ; auto:default_target <abc2_target> ; auto:overwrite root:4 ].", \
                        f"<{mycommand}> auto:uses <abc2> .", \
                        f"<abc2> a auto:argument ; auto:default <abc2_target> ; auto:default_target <abc2_target> ; auto:overwrite root:4 .", \
                        f"<abc2_target> a auto:data .", \
                        ))
            created_resources = "\n".join(( f"@base <{self.test_path_url}> . ", \
                        f"@prefix root: <{self.test_path_url}> . ", \
                        f"@prefix auto: <http://program/automaton#> . ", \
                        f"@prefix owl: <http://www.w3.org/2002/07/owl#> . ",\
                        f"<{tmpurl}> a auto:data .", \
                        f"<abc3> <a> <{tmpurl}> .",\
                        f"<abc3> auto:created <{tmpurl}> .",\
                        f"<abc2> auto:created <abc2_target> .",\
                        ))

            #intro at end
            asd = rl.ontology_organizer.load( useprogram.uri_to_class, rdf_resource, extra_resources, created_resources )
            old_axioms = list( asd.rdfgraph )
            program = filter( lambda x: type(x)==useprogram.program_container, \
                        asd.to_dict()[self.program_url] ).__next__()
            ret, newresources = program()
            new_axioms = [ x for x in asd.rdfgraph if x not in old_axioms ]

        #confirming all happened as planned
        found_new_originates = set( v for v in new_axioms \
                if v[1]==rdflib.term.URIRef("http://program/automaton#originates") )
        self.assertEqual( len(found_new_originates), 2, "Couldnt find all "
                        "needed originates from newly generated "
                        "data to placeholders" )
        found_new_exampleproperties = set( v for v in new_axioms if \
                v[1]==rdflib.term.URIRef("http://example.com/my#property") )
        self.assertEqual( len(found_new_exampleproperties), 1, 
                        msg="Algorithm hasnt created new statement containing "
                        "the example property, which should be assessed for "
                        f"newly created resources {list(new_axioms)}" )

def _util_rdfgraph_to_owlready_onto( mygraph:rdflib.Graph, world, onto=None ):
    """

    :type onto: owlready2.namespace.Ontology (return of get_ontology)
    :param onto: save data in this ontology
    """
    import tempfile
    import owlready2 as owl
    with tempfile.NamedTemporaryFile() as rdf_information:
        with open( rdf_information.name, "w" ) as qq:
            qq.write( mygraph.serialize( format="ntriples" ) )
        #print( myg.serialize() )
        tmp_onto = world.get_ontology( rdf_information.name )
        tmp_onto.load()
    if onto:
        onto.imported_ontologies.append( tmp_onto )
    return tmp_onto


def util_load_owlonto_from_turtle( filepath ):
    with tempfile.NamedTemporaryFile( mode="w" ) as tmpfile:
        automaton_baseinfo = rdflib.Graph()
        automaton_baseinfo.parse( filepath )
        with open( tmpfile.name, "w" ) as ff:
            ff.write( automaton_baseinfo.serialize( format="ntriples" ) )
        onto = owl.get_ontology( tmpfile.name )
        onto.load()
    return onto

        
if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
