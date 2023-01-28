rdf loader
----------

.. code:: python

        g = rdflib.Graph().parse( data=f"""@base <http://example.com/> .
            <1> a <{testinfo.obj1}> .
            <1> <{testinfo.prop1}> <2> .
            <2> a <{testinfo.obj2}>.
        """)

        objects:dict = rl.load_from_graph( testinfo.input_dict, g )
        # objects == { 
        #        URIRef("http://example.com/1"): [obj1, ...],
        #        URIRef("http://example.com/2"): [obj2, ...],
        #        }



.. automodule:: rdfloader.rdf_loader
   :members:
   :undoc-members:
   :show-inheritance:
