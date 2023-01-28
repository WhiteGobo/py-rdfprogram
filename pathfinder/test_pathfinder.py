import unittest
import os.path
from .. import useprogram
from .. import rdf_loader as rl
from . import main
import logging
import rdflib
import importlib.resources
from . import testsrc


class TestProgramPathfinder( unittest.TestCase ):
    def test_simple( self ):
        testsrc_info1 = importlib.resources.path( testsrc, "info1.ttl" )
        #g = rdflib.Graph()
        #g.parse( testsrc_info1 )
        uri_to_class = {}
        uri_to_class.update( useprogram.uri_to_class )
        uri_to_class.update( main.uri_to_class )
        asd = rl.ontology_organizer.load( uri_to_class, testsrc_info1 )
        qwe = ( x for x in asd if type(x)==main.factory_graph ).__next__()
        qwe()
        raise Exception( asd.to_dict() )
        main.factoryleaf.from_rdfprogram
        pass

if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
