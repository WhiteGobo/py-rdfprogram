.. automatic-generation-pathfinder documentation master file, created by
   sphinx-quickstart on Tue Nov 15 11:19:14 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to automatic-generation-pathfinder's documentation!
===========================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   streamlined_intro
   ideas
   graphstate
   flowgraph
   autocomplete_graph
   autodoc_base


Next things to do
=================

New file with all rdf-resources necessary
-----------------------------------------


Rewrite autocomplete algorithm
------------------------------

I should rewrite the code of :py:meth:`lin_flowgraph_abstract.rdfgraph_flowgraph.complete_datagraph`.
The maximalgraphs will be created from the targetgraph. the inputgraphs then 
will be search for by sparql search. In every search there must be mutable 
resources originating from the targetgraph and temporary assigned nodes to 
the targetgraph. if a new node validates in a partstructure of the 
targetgraph as new resource, it will be a temporary assigned node. For this 
node new sparql searches will be created for the inputgraphs of the flowgraph

mutable Nodes in the inputgraph generate sparql searches for temporary 
assigned  nodes. Each neighbouring mutable resource in the targetgraph to 
the inputgraph will result in one sparql search. All properties and all 
connections of a temporary assigned node and the already existing nodes is 
to be created. Each time a temporary node is created new searches will be 
created, treating the temporary assigned node as "already in the inputgraph 
existing" node.

The algorithm completes if a sparql search for the whole targetgraph works.
properties of mutable resources in the inputgraph can be ignored and the 
mutable resources can be instead be used  directly in properties of the 
targetgraph.

After new inputgraphs are found, new possible program are created. They are stored in the global_rdfgraph in the form:

.. code:: ttl

   @prefix mything: <http://mein.program/> .
   program a mything:program;
        mything:parameters [ _:1, _:2 ].

   [ a mything:command;
   _:1 _:value1 ;
   _:2 _:value2 ;
   mything:priority 1.5
   ]

In each step the program with the lowest priority will be executed. New resources can be evaluated by the prior named sparql searches.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
