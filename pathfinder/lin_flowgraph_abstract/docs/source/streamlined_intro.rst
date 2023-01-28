Introduction/ Howto
===================

Creating programs for automatic processing
------------------------------------------

.. todo::
   Introduction how to create an implementation of _graphstate.program

.. todo::
   Create default implementation of _graphstate.program

All executable function must be packed into an implementation of the abstract 
class :py:class:`_graphstate.program<lin_flowgraph_abstract._graphstate.program>`.
You can either use the default implementation :py:class:`default_program_class` or you can create an own implementation as described here

To pack a function into the default implementation you deliver just a call function an inputgraph and an outputgraph.

.. todo::
   Better introduction to how to pack a function into the object 
   _graphstate.program


Creating flowgraphs from programs
---------------------------------

For the creation of the flowgraph you can use the method :py:meth:`flowgraph.from_programs<lin_flowgraph_abstract.flowgraph.from_programs>`.

.. code:: python

    myflow = flowgraph.from_programs( [ self.testprogram ], graphstate.graphstate.spawn_starting_states_from_program )


You can find possible generationflow with the method :py:meth:`flowgraph.create_directionmap_for_output<lin_flowgraph_abstract.flowgraph.create_directionmap_for_output>`

Possible Programs for the transition from one or between two states can be found with the method :py:meth:`flowgraph.from_programs<lin_flowgraph_abstract.flowgraph.from_programs>`

target information to a graph
-----------------------------


Creating new information from datagraph
---------------------------------------


Use class :py:class:`rdfgraph_flowgraph<lin_flowgraph_abstract.rdfgraph_flowgraph>`

.. code::

        myflow2 = create_program_from_datagraph.rdfgraph_flowgraph.from_programs( \
                        [ self.testprogram, self.testprogram3 ], \
                        graphstate.graphstate_onlynodes.spawn_starting_states_from_program )


implement class :py:class:`lin_flowgraph_abstract.create_program_from_datagraph.program_iterator`
and use its method 
:py:meth:`from_flowgraph<lin_flowgraph_abstract.create_program_from_datagraph.program_iterator.from_flowgraph>`.


.. code::

        #create_program_from_datagraph.complete_datagraph( myflow2, wholegraph )
