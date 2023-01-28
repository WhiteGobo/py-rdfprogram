Flowgraph
=========

Description
-----------

Flowgraphs describe what new information can be created with a given 
graphstate and given programs. Each graphstate in the flowgraph is a 
connected information graph.


How flowgraphs build themselves
-------------------------------

The standard method for creation is :py:meth:`flowgraph.from_programs<lin_flowgraph_abstract.flowgraph.from_programs>`.
Creation takes the inputstates of the programs as startpoints. Each graphstate 
will be tried as input for each program. If the graphstate contains a valid 
inputstate, new graphstates will be developed via the method 
:py:meth:`spawn_prev_state_from_program<lin_flowgraph_abstract.graphstate.spawn_next_state_from_program>`
with the possible new axiom of the program.

Every state tries to create parents and offspring with each program and the 
generated states will be added to the flowgraph. Parents will be created via 
its method :py:meth:`spawn_prev_state_from_program<lin_flowgraph_abstract.graphstate.spawn_prev_state_from_program>`.
Offspring will be created via its method :py:meth:`spawn_next_state_from_program<lin_flowgraph_abstract.graphstate.spawn_next_state_from_program>`
For each generated offspring a new edge will be added to the flowgraph 
between inputstate and possible new states after the usage of a program.
On Each edge will be saved, which program was used and what the new axioms 
are to generate the new graphstate.

If a state has a parentstate from a via a certain program, the method :py:meth:`spawn_prev_state_from_program<graphstate.graphstate.spawn_next_state_from_program>`
wont be used to create new state with this program. This limits the number of
states that are generated in the creation process. 


extra thingis
-------------

.. automodule:: _flowgraph
   :members:
