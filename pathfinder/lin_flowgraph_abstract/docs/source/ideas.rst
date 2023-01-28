Ideas
=====

informationgraphs and graphstates
---------------------------------

Information is presented as described in RDF (Resource Description Framework).
So its assumed readers of this documentation are knowledgeable about RDF.

So the idea is, that we can describe the information, we want to achieve in an abstract form in a knowledge-graph. This graph describes the properties of the resources we want to generate, but not the resource completely.

For example if we want to have the sum (target) of 2 and 3, the resource would be described something like this:

.. code ::

   @prefix math: <http://example.org/math>.
   <target> math:sum_over { 2 3 } .

To generate the requested resources the computer can use, what we will call programs. Everything can be used as program as long as its required inputs and the information, that will be created can be described by a knowledge graph. Here we differentiate between immutable resources and mutable resource, as all mutable resources are representative for an inputvariable of the program.

For example a program that sums up two numbers would have an outputgraph like:

.. code :: ttl

   @prefix math: <http://example.org/math>.
   @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
   _:in1 a rdfs:Literal .
   _:in2 a rdfs:Literal .
   _:out math:sum_over { _:in1 _:in2 } ;
        a rdfs:Literal .

the inputgraph:

.. code :: ttl

   @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
   _:in1 a rdfs:Literal .
   _:in2 a rdfs:Literal .

Every mutable resource is to be described as a Bnode and each immutable resource cant be a BNode. immutable Resources labeled as BNode are to be relabed in the context of the program to an URI:
So nodes like:

.. code :: ttl

   _:resource a rdf:Thing .

is to be formatted to:

.. code :: ttl

   <resource> a rdf:Thing .

All resources are constant. So programs should always give the same output 
for the same input resources. You cant for example use simple sensors as 
input, which would return everytime a different value, when they are read.

program and its input and outputs
---------------------------------

All possible results of the program are to be described by new axioms. So only if the program fails there are no new axioms. Categorizing programs should therefore fail, when categorization is false.
Each program has exactly one valid inputstate.

Following conditions must be met by the inputstate and the outputstate:
* all axioms must contain one mutable Resource
* The outputstate must be connected

Yet only programs are useable, which generated only axioms, which contain one 
mutable resource.
Each program has exactly one possible inputgraph. But the result of one 
program can differ from the inputgraph used. So for simplification purposes, 
just all possible new axioms will be given for one program.

