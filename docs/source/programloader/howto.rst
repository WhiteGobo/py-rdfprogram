Example Implementations
=======================


Example Graph in turtle(ttl)
----------------------------

The next turtle file describes how to execute a program. I will give a short 
normal explaination.

The program at "path/to/executable" will be used. We have knowledge
about 2 input arguments. The first is a positional argument at position zero
and the second is a keyword-argument with the keyword "--savefile".
We can execute the app asdf:meinBefehl and that app executes our program.
It uses as first argument 5 and as second argument a fileposition.
The fileposition is a little bit tricky because we use not a
uri as input but a blanknode. programloader will just create a temporary file
as placeholder for this resource and will give back the position of that file.
The two arguments of the program are described by _:res1 and _:res2 .
If a resource is updated, all axioms of the correlated mutable_resource
will be added. The mutable resource will be replaced in those axioms with
the used argument.


.. code:: ttl

            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            # This is the description of the program
            <file://path/to/executable> a proloa:program ;
                proloa:hasArgument _:1, _:2 .
            _:1 proloa:id 0 ;
                a proloa:arg .
            _:2 proloa:id "--savefile" ;
                a proloa:arg .

            # This is the description, how the program should be executed
            asdf:meinBefehl proloa:executes <file://path/to/executable> ;
                a proloa:app ;
            # first argument is the integer 5
                _:1 5 ; 
            # this resource will be used as second argument. See description
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

After the execution of the app asdf:meinBefehl the algorithm will return
the output printed to stdout and a list of axiom.

.. code:: python

        for axiom in new_axioms:
                g.update( axiom )
        print( g.serialize() )

        >> ...
        >> asdf:meinBefehl proloa:executes <file://path/to/executable> ;
        >>      a proloa:app ;
        >>      _:1 5 ; 
        >>      _:2 [
        >>              a proloa:link; 
        >>              asdf:customProp3 5; 
        >>              asdf:customProp1 asdf:customResource1
        >>              ].
        >> ...



Code implementation
-------------------

See programloader/test.py for a working implementation.

.. code:: python

        import rdfloader as rl
        import programloader
        import rdflib

        g = rdflib.Graph().parse( format="ttl", data=f"""
            @prefix asdf: <http://example.com/> .
            @prefix proloa: <http://example.com/programloader/> .
            [...]
            asdf:meinBefehl proloa:executes <file://path/to/executable> ;
                a proloa:app ;
            [...]
        """)
        all_objects: dict = rl.load_from_graph(programloader.input_dict, g)

        app_iri = URIRef("http://example.com/meinBefehl")
        returnstring, new_axioms = all_objects[ app_iri ][0]()
