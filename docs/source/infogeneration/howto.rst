infogeneration introduction
===========================

A simple example
----------------

The automatic generation of data builts on top of the package programloader 
and rdfloader.
So its assumed that the reader understands how to use rdfloader and 
programloader.

The package infogeneration provides a way to automaticly generate information.
The main workhorse for this is the class infogeneration.tactic (autgen:tactic)
and the class infogeneration.project (autgen:project).

For given programs <programs:p1> and <programs:p2> a minimal implementation
of a tactic looks like this:

.. code:: ttl

    #/path/to/file.ttl
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix autgen: <http://example.com/automaticgenerator#> .
    @prefix programs: <file://somewhere/on/your/computer/> .
    @prefix ex: <http://example.com/ex#>.

    ex:mytactic a autgen:tactic ;
        autgen:uses programs:p1 ,
                    programs:p2 .
        autgen:target <target_information> .

    <source_information> rdfs:comment "Here should be some axioms" .
    <target_information> rdfs:comment "Here should be some axioms" .
    programs:p1 rdfs:comment "Here should be some axioms" .
    programs:p2 rdfs:comment "Here should be some axioms" .
    (...)

A autgen:project can then be implemented further:

.. code:: ttl

   (...)
   <myProject> autgen:uses <mytactic> ;
                autgen:create <target> .
   <target> a custom_props:number .


How the target can be described will be explained in the chapter 
Describing the target.
The :py:class:`tactic` (here: mytactic) can be loaded with the rdfloader package.
The inputdictionary for :py:meth:`rdfloader.load_from_graph` is provided as 
infogeneration.input_dictionary.

.. code:: python

        #/usr/bin/env python
        import rdflib
        import rdfloader as rl
        from infogeneration import tactic
        from infogeneration import input_dictionary
        g = rdflib.Graph().parse("/path/to/ttl-file")
        generated_objects = rl.load_from_graph(input_dictionary, g)
        myProject_uri = rdflib.URIRef("http://example.com/ex#myProject")
        myProject: tactic = generated_objects[myProject_uri][0]
        ...


Now the information can be automaticly generated via the methods 
get_priorities and execute_first_app:


.. code:: python

   ...
   save_directory = "path/for/extra_data/"
   tmp_newinfo: rdflib.graph._TripleType #axioms for rdflib
   while myProject.get_priorities():
        tmp_newinfo = myProject.execute_first_app()
   #if target information is described via BNodes
   tmp_newinfo = myProject.put_data_in_directory(save_directory)
   #if you need to save the axioms
   for ax in tmp_newinfo:
        g.add(ax)


Describing the source and the target
------------------------------------

The source and the target must be described according to how the given
programs handle information.

.. code:: ttl

        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix custom_props: <http://example.com/> .
        @prefix proloa: <http://example.com/programloader/> .
        @prefix programs: <file://somewhere/on/your/computer/> .
        @prefix adder: <file://adder#> .

        programs:add_one a proloa:program ;
            rdfs:comment "add one to a number" .
            proloa:hasArgument _:add1, _:add2 .
        adder:add1 proloa:id 0 ;
            rdfs:comment "loadfile" ;
            a proloa:arg ;
            proloa:describedBy _:addres1 .
        adder:add2 proloa:id 1 ;
            rdfs:comment "savefile" ;
            a proloa:arg ;
            proloa:declaresInfoLike _:addres2 .

        _:addres1 a proloa:mutable_resource ;
            a custom_props:number .
        _:addres2 a proloa:mutable_resource ;
            a custom_props:number .
        _:addres1 custom_props:smaller _:addres2 .
        custom_props:number rdfs:comment "file with a number inside" .
        custom_props:greater rdfs:comment "subject is smaller than object" .

A short description of the shown program programs:add_one:
One-line desription, what the program and the properties stand for are given 
via rdfs:comment.
The program uses two inputs. The first input should comparable(see programloader mutable_resource) to _:addres1.
The second input describes where the output should be generated. If the file 
exists(see programloader) after the execution of an app, descending from the
program, all given axioms, so (_:addres2 a custom_props:number)
and (_:addres1 custom_props:smaller _:addres2).

The source needs, and the target will be generated with information that is
also described via given (resources classified as) proloa:mutable_resource's.

.. code:: ttl

        @prefix custom_props: <http://example.com/> .

        <source> a custom_props:number .
        <target> a custom_props:number .
        <source> custom_props:smaller <target> .

Only the target has to be linked to a project. The project will gather 
automaticly all available useable resource, when first called 
:py:meth:`get_priority`. All linked targets to the project will be considered
as missing.

.. code:: ttl

        <myproject> autgen:uses <mytactic> ;
                autgen:create <target> .
