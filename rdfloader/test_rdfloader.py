"""

:todo: somehow this seems to make errors because it doesnt recognise needed=False:
    class has_bnode_property( base ):
        def __init__( self, uri, val: ext.info_custom_property(property_type), 
                        val2: ext.info_attr( prop2, needed=False ) ):
"""
import unittest
try:
    from . import rdf_loader as rl
except ModuleNotFoundError:
    import rdf_loader as rl
from . import extension_classes as ext

import itertools as it
import logging
logger = logging.getLogger()
import rdflib
from . import RDF
from . import classloader_objectcreator as cloc

class TestRDFLoader( unittest.TestCase ):
    def test_load_new_information(self):
        """Load new resources, that are dependent on already built resources
        """
        old_res = rdflib.URIRef("http://example.com/2")
        old_resources = {old_res: testinfo.empty(old_res)}
        g = rdflib.Graph().parse(data="""@base <http://example.com/> .
            <1> a <{testinfo.obj1}>;
            <{testinfo.prop1}> <2>.
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g, old_resources )
        self.assertEqual(set(it.chain(g.subjects(),old_resources)),
                         set(qwe.keys()))

    def test_simple( self ):
        """Tries simple load. <1> and <2> are loadable but <3> is not. \
        But <2> doesnt require <3>. \
        The loaded data (qwe) should be {<1>:... , <2>: ... }

        :todo: i would like to also test, if the returned object have the
            expected type, or at best are the expected object.
        """
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj1}> .
            <1> <{testinfo.prop1}> <2> .
            <2> a <{testinfo.obj2}>.
        """)

        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ), \
                                "couldnt create all described resources. "\
                                "if 2 is missing generally no objects "\
                                "could be created. If only 1 is missing "\
                                "something went wrong, with the dependencies")

        #test same but dont give any wanted_resources
        wanted_resources = [
                                rdflib.URIRef("http://example.com/1"),
                                #rdflib.URIRef("http://example.com/2"),
                                ]
        qwe = rl.load_from_graph( testinfo.input_dict, g, wanted_resources )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ), \
                                "The algorithm doesnt considers all "\
                                "resources automaticly as wanted. "
                                "That would be the expected result.")
        self.assertEqual( qwe[ rdflib.URIRef("http://example.com/1") ][0].val,
                         qwe[rdflib.URIRef("http://example.com/2") ][0] )

        #Test that load_from_graph only loads wanted_resources
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj2}> .
            <2> a <{testinfo.obj2}>.
        """)
        wanted_resources = [
                                rdflib.URIRef("http://example.com/1"),
                                #rdflib.URIRef("http://example.com/2"),
                                ]
        qwe = rl.load_from_graph( testinfo.input_dict, g, wanted_resources )
        self.assertEqual( set(wanted_resources), set(qwe.keys() ))


    def test_skipattribute(self):
        #g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
        #    <1> a <{testinfo.obj5}> .
        #    <1> <{testinfo.prop1}> <2> .
        #    <2> a <{testinfo.obj2}> .
        #""")
        #qwe = rl.load_from_graph( testinfo.input_dict, g )
        #self.assertEqual(set(g.subjects()), set(qwe.keys() ))

        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj5}> .
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual(set(g.subjects()), set(qwe.keys()))


    def test_dependencyskip( self ):
        """Tries to load objects, where the dependencies are not loadable \
        <3> is not loadable and <2> requires <3> as input
        """
        logger.debug("first part")
        #This should fail because missing Resource to attribute
        with self.subTest( "asdf" ):
            g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
                <1> a <{testinfo.obj1}> .
            """)
            qwe = rl.load_from_graph( testinfo.input_dict, g )
            self.assertEqual( qwe, dict(), msg="Could load despite missing "\
                                                "dependencies" )

        logger.debug("second part")
        #<1> should be removed at the end of algorithm, because it couldnt
        #get any valid resource for attribute
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj4}> .
            <1> <{testinfo.prop1}> <2> .
            <2> a <{testinfo.obj1}>.
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertTrue(rdflib.URIRef("http://example.com/2") not in qwe,
                         msg=f"Loaded unloadable resource")
        self.assertEqual( qwe, dict(), msg="Could load despite missing "\
                                            "dependencies" )

        logger.debug("third part")
        #<1> should be removed at the end of algorithm, because <2> got 
        #removed in the algorithm
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj4}> .
            <1> <{testinfo.prop1}> <2> .
            <2> a <{testinfo.obj4}>.
            <2> <{testinfo.prop1}> <3> .
            <3> a <{testinfo.obj1}>.
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(qwe), set(), msg="Could load despite missing "\
                                            "dependencies" )

    def test_circledependency( self ):
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj4}> .
            <1> <{testinfo.prop1}> <2> .
            <2> a <{testinfo.obj4}>.
            <2> <{testinfo.prop1}> <1> .
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        #self.assertEqual( qwe[ rdflib.URIRef("http://example.com/1") ][0].val,
        #                 qwe[rdflib.URIRef("http://example.com/2") ][0] )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ) )

        a = qwe[ rdflib.URIRef("http://example.com/1") ][0]
        b = qwe[ rdflib.URIRef("http://example.com/2") ][0]
        self.assertEqual( a.val, b )
        self.assertEqual( b.val, a )


    def test_iter( self ):
        """Tests if list attributes are loaded correctly"""
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj3}> .
            <1> <{testinfo.prop3}> <2>, <3> .
            <2> a <{testinfo.obj2}>.
            <3> a <{testinfo.obj2}>.
            """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertIn( rdflib.URIRef("http://example.com/1"), qwe)
        val3 = qwe[ rdflib.URIRef("http://example.com/1") ][0].val3
        self.assertEqual( set(val3),
                         {qwe[rdflib.URIRef("http://example.com/2") ][0],
                         qwe[rdflib.URIRef("http://example.com/3") ][0] })

    def test_dict_properties( self ):
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.has_bnode_property_obj}> .
            <2> a <{testinfo.obj2}> .
            <p1> a <{testinfo.property_type}> .
            <1> <p1> <2> .
            """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertTrue( rdflib.URIRef("http://example.com/1") in qwe )

        mydict = qwe[ rdflib.URIRef( "http://example.com/1" ) ][0]
        mykey = qwe[ rdflib.URIRef( "http://example.com/p1" ) ][0]
        myval = qwe[ rdflib.URIRef( "http://example.com/2" ) ][0]
        self.assertEqual( mydict.val, {mykey:myval} )

    def test_blanknode_properties( self ):
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.has_bnode_property_obj}> .
            <2> a <{testinfo.obj2}> .
            _:prop1 a <{testinfo.property_type}> .
            <1> _:prop1 <2> .
            """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        #self.assertTrue( rdflib.URIRef("http://example.com/1") in qwe )
        self.assertTrue( set(qwe.keys()), set(g.subjects()))
        #raise Exception( qwe )

    def test_anyedge( self ):
        g = rdflib.Graph().parse( format="ttl", data=f"""@base <file://a/> .
            @prefix x: <http://example.com/a/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            <1> x:prop1 x:obj1 ;
                a <{testinfo.any_prop_obj}> .
            <2> a <{testinfo.property_type}> .#no outgoing edges
            <1> x:prop3 <2> .
            """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(g.subjects()), set(qwe.keys()))

        g2 = rdflib.Graph().parse( format="ttl", data=f"""@base <file://a/> .
            @prefix x: <http://example.com/a/> .
            <1> x:prop1 x:obj1 .
            <1> x:prop3 <2> .
            """)
        self.assertEqual( set(qwe[rdflib.URIRef("file://a/1")][0].axioms),
                         set(g2) )

    def test_Literal( self ):
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj1}> .
            <1> <{testinfo.prop1}> "123" .
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ), \
                                "1 is dependend on generation of int '123'" )

        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj3}> .
            <1> <{testinfo.prop1}> "123" .
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ), \
                                "couldnt create all described resources. "\
                                "if 2 is missing generally no objects "\
                                "could be created. If only 1 is missing "\
                                "something went wrong, with the dependencies")

        return
        raise NotImplementedError( "here something with dictionary should be used as object" )
        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj3}> .
            <1> <{testinfo.prop1}> "123" .
        """)
        qwe = rl.load_from_graph( testinfo.input_dict, g )
        self.assertEqual( set(g.subjects()), set(qwe.keys() ), \
                                "couldnt create all described resources. "\
                                "if 2 is missing generally no objects "\
                                "could be created. If only 1 is missing "\
                                "something went wrong, with the dependencies")


prop1 = "a://property1"
prop2 = "a://property2"
prop3 = "a://property3"
property_type = rdflib.URIRef( "a://property_type" )
ignoredprop = rdflib.URIRef("a://ignored_property")
any_prop_obj = rdflib.URIRef( "a://anyprop_object" )
class base:
    def __repr__( self ):
        return f"<{type(self)}:{self.uri}>"

class testinfo:
    obj1 = rdflib.URIRef( "a://object1" )
    obj2 = rdflib.URIRef( "a://object2" )
    obj3 = rdflib.URIRef( "a://object3" )
    obj4 = rdflib.URIRef( "a://object4" )
    obj5 = rdflib.URIRef( "a://object5" )
    any_prop_obj = any_prop_obj
    has_bnode_property_obj = rdflib.URIRef( "a://hasbnode_object" )
    #prop1 = rdflib.URIRef( "a://property1" )
    #prop2 = rdflib.URIRef( "a://property2" )
    #prop3 = rdflib.URIRef( "a://property3" )
    #property_type = rdflib.URIRef( "a://property_type" )
    prop1 = prop1
    prop2 = prop2
    prop3 = prop3
    property_type = property_type
    ignoredprop = ignoredprop
    class has_bnode_property( base ):
        def __init__( self, uri, val: ext.info_custom_property(property_type) ):
            self.uri = uri
            if not isinstance( val, dict ):
                raise TypeError( f"val should have been a dict: {val}")
            self.val = val

    class A( base ):
        def __init__( self, uri, val: ext.info_attr( prop1 )):
            self.uri = uri
            self.val = val
            if not isinstance( self.val, (base, int, str, float) ):
                raise TypeError( self.val, type(self.val) )
    class B( base ):
        def __init__( self, uri, val1: ext.info_attr( prop2, needed=False ) =None ):
            self.uri = uri
            self.val1 = val1
            if self.val1 is not None:
                if not isinstance( self.val1, (base, int, str, float) ):
                    raise TypeError( self.val1 )
    class C( base ):
        def __init__( self, uri, val3: ext.info_attr_list( prop3 )):
            self.uri = uri
            self.val3 = list( val3 )
            if not all( isinstance( x, (base, int, str, float) ) for x in self.val3 ):
                raise TypeError( self.val3, )
    class D( base ):
        def __init__(self, uri, val: ext.info_attr(prop1, needed=True) = None):
            self.uri = uri
            if val is not None:
                self.val = val

        def _set_val(self, val):
            if not isinstance( val, (base, int, str, float) ):
                raise Exception(val)
                raise TypeError(val)
            self._val = val

        def _get_val(self):
            try:
                return self._val
            except AttributeError:
                return None

        val = property(fget=_get_val, fset=_set_val)

    class E( base ):
        def __init__( self, uri, val: ext.info_attr(prop1, needed=False)=None):
            self.uri = uri
            if val is not None:
                self.val = val
                if not isinstance( self.val, (base, int, str, float) ):
                    raise TypeError( self.val )
    class empty( base ):
        def __init__( self, uri ):
            self.uri = uri

    class any_prop_class:
        def __init__(self, uri, axioms:ext.info_anyprop([ignoredprop],[(RDF.a,any_prop_obj)])):
            self.uri = uri
            self.axioms = axioms

    input_dict = { 
            obj1: A,
            obj2: B,
            obj3: C,
            obj4: D,
            obj5: E,
            any_prop_obj: any_prop_class,
            has_bnode_property_obj: has_bnode_property,
            property_type: empty,
            }


if __name__=="__main__":
    logging.basicConfig( level=logging.DEBUG )
    unittest.main()
