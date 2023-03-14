"""This module delivers all things needed to find a way to generate
certain information. It uses for this a method to calculate the distance 
between available information and information about, which program 
needs and generates, what information.

The information about the programs is used to make first a little pathgraph 
between different information graphs and then a big pathgraph between 
informationgraphs. These pathgraphs show, what information can be produced
locally and globally from existing information.

The distance between available information is used to find out, which
information lies nearest to the needed information. The idea is, that
the programs can make little improvements to the available data. So
step by step the information created gets nearer and nearer to the information
we search for.
"""
