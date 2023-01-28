def __rebase_for_documentation__( x ):
    """Autodoc now will handle this thing as thing from mother module"""
    x.__module__ = __name__
# Methods and Classes
from ._flowgraph import flowgraph
from ._graphstate import graphstate, graphstate_onlynodes
flowgraph.__module__ = __name__
graphstate.__module__ = __name__
from .create_program_from_datagraph import program_iterator, rdfgraph_flowgraph
__rebase_for_documentation__( program_iterator )
__rebase_for_documentation__( rdfgraph_flowgraph )

# Constants

# Abstractmethods and classes
from ._flowgraph import Program, Edge_program, GraphState, FLOWGRAPH_EDGEMAP
from ._graphstate import information_placeholder, program_attribute, program
