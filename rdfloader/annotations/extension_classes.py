"""This module contains all classes that should be used for extending
the rdf_loader with python-classes. The 
function :py:meth:`rdf_loader.load_from_graph` 
needs :py:class:`extension_classes.constructor_annotation` as annotations
for the python-constructors.
"""
from __future__ import annotations
import dataclasses
import rdflib
import logging
import abc
logger = logging.getLogger( __name__ )
import typing as typ
import itertools as it

from .. import RDF


class _objectcontainer(abc.ABC):
    uri: rdflib.IdentifiedNode
    obj: object
    def __hash__(self):
        pass

INPUTGENERATOR = typ.Callable[
        typ.Dict[rdflib.IdentifiedNode, _objectcontainer], 
        typ.Iterator[typ.Tuple[object, typ.List[_objectcontainer]]]
        ]
"""Generator needed by load_from_graph algorithm. Generates possible
parameter-inputs or attribute-inputs for given resource.
"""

#Inputgenerator = typ.Callable
#"""Creates the input for the given attribute attr. This can be 
#directly used as input for the constructor or used in a dictionary 
#used as **dict for the constructor. Doesnt raise KeyError, when 
#expected uri isnt in uri_to_pythonobject.
#
#:param attr: Argument of the constructor, for which, the pythonobject 
#        should be searched for.
#:type attr: str
#:param uri_to_pythonobject: Mapping to find generated pythonobjects
#:type uri_to_pythonobject: dict[ rdflib.IdentifiedNode, list[object] ]
#"""


class constructor_annotation( abc.ABC ):
    """Every annotation of loadable objects in the load_from_graph
    algorithm must be an subclass of (or feasible as) this class.
    """

    @property
    @abc.abstractmethod
    def inputtype(self) -> type:
        """Specifies the type of the argument, that is delivered, when this
        annotation is used for a parameter or an attribute. Is not really
        used yet. Is only for documentation purposes.

        This type should match the type of the first part of the returnvalue
        of the INPUTGENERATOR, that is yielded by create_input_generator:

            >>> gen = anno.create_input_generator(...)
            >>> for value, resourcelist in gen(...):
            >>>     #Here value conforms with anno.type
            >>>     (...)

        Typecontrol will not be added because of 'duck typing'. For 
        typecontrol please implment this by yourself as property or 
        in __init__. As Example:

            >>> def __init__(self, val: anno(type=int, ...)):
            >>>     self.val = int(val)

        or as property:
            
            >>> def __init__(self, val: anno(type=myclass)):
            >>>     (...)
            >>> 
            >>> @property.set
            >>> def val(self, val):
            >>>     if not hasattr(val, "myclass_method1"):
            >>>         raise TypeError(val)

        """
        pass

    uri: str
    """This might not be nneded anymore"""

    needed: bool
    """Resources can be optional or needed. If the attribute has a
    default value, the resource is always needed and this option
    will be ignored.
    """

    at_generation: bool
    """If the resource has a default value and the resource is not needed,
    this option specifies, if the resource can be set after the creation.
    In any other case, this option will be ignored
    """

    # to_uri_identifier seems optional as long as uri is provided
    #@abc.abstractmethod
    #def to_uri_identifier( self ):
    #    pass
    @abc.abstractmethod
    def find_objects( self, rdf_graph: rdflib.Graph, \
                        uri_subject: rdflib.IdentifiedNode ):
        """This method will be called by the algorithm load_from_graph
        to identify how which resources, and how they will be used as 
        input for the annotated attribute

        :TODO: This method should be obsolete but it isnt yet. Please
            change!!!
        """
        pass

    @abc.abstractmethod
    def find_dependencies( self, rdf_graph : rdflib.Graph, \
            uri_subject: rdflib.IdentifiedNode) \
            -> typ.Iterable[(rdflib.Identifier, rdflib.Literal)]:
        """Returns the same IRIs as in find_objects but all IRIs will
        be returned in a simple list. Just to get all dependencies in
        a standard format.
        """
        pass

    @abc.abstractmethod
    def create_input_generator(self, rdf_graph:rdflib.Graph, 
                               uri_subject:rdflib.URIRef) -> INPUTGENERATOR:
        """Creates a generator object, which can generate the input
        for method if given a mapping of IRIs to all available
        python-objects

        :param rdf_graph: Graph which describes all possible available 
            resources.
        :param uri_subject: Resource name for which the input is searched for
        :returns: a generator needed by load_from_graph. See 
            :py:object:`INPUTGENERATOR` for more information.
        """
        def input_generator(uri_to_pythonobjectcontainers: typ.Dict[rdflib.IdentifiedNode, _objectcontainer]) -> typ.Iterator:
            pass

Uri = str
"""type hint equal to strings. Given Uri have this type"""

class info_anyprop(constructor_annotation):
    """This annotates, that all axioms should be found, which arent
    excluded explicitly. All axioms will be returned as axioms
    and wont be given as python-objects.

    :param ignore_uris: all axioms, which have one of these IRIs
        used as property, will be ignored.
    :type ignore_uris: list[IRI]
    :param ignore_axioms: all axioms, which uses one of these IRI-pairs
        as property and object will be ignored.
    :type ignore_axioms: list[(IRI, IRI)]
    """
    inputtype = "rdflib.graph._TripleType"
    needed = True
    def __init__(self, ignore_uris: typ.List[rdflib.IdentifiedNode], 
                 ignore_axioms: typ.List[typ.Tuple[rdflib.IdentifiedNode, rdflib.IdentifiedNode]],
                 at_generation = False):
        self._axioms=None
        self.ignore_axioms = ignore_axioms
        self.ignore_uris = list(ignore_uris)
        self.at_generation = at_generation
        assert all(isinstance(x, rdflib.IdentifiedNode) \
                for x in self.ignore_uris)

    def __repr__(self):
        name = ".".join((type(self).__module__, type(self).__name__))
        a = [tuple(x) for x in self.ignore_uris]
        b = [tuple(str(y) for y in x) for x in self.ignore_axioms]
        return f"<{name}: {a}: {b}>"

    def __str__(self):
        a = [tuple(x) for x in self.ignore_uris]
        b = [tuple(str(y) for y in x) for x in self.ignore_axioms]
        return f"<{type(self).__name__}: {a}: {b}>"

    def to_uri_identifier(self):
        return self

    def create_input_generator(self, rdf_graph, uri_subject):
        """asdf

        :param rdf_graph: qwer
        """
        axioms = []
        for _, prop, subj in rdf_graph.triples((uri_subject, None, None)):
            if not any((\
                    prop in self.ignore_uris, \
                    (prop,subj) in self.ignore_axioms, \
                    )):
                axioms.append((uri_subject,prop, subj))
        def input_generator(iri_to_pythonobject):
            yield axioms, [] #The axioms may be needed to be changed in a way

        return input_generator

    def find_objects(self, rdf_graph, uri_subject):
        yield []

    def find_dependencies( self, rdf_graph, uri_subject):
        return []


@dataclasses.dataclass
class info_attr_list( constructor_annotation ):
    """Annotated Attribute will get a list of objects as input. For each 
    possible input a corresponding object will be used.
    """
    uri: str
    needed: bool = True
    at_generation: bool = False
    inputtype: type = type

    def __repr__(self):
        name = ".".join((type(self).__module__, type(self).__name__))
        a = [tuple(x) for x in self.ignore_uris]
        b = [tuple(str(y) for y in x) for x in self.ignore_axioms]
        return f"<{name}: {a}: {b}>"

    def __str__(self):
        a = [tuple(x) for x in self.ignore_uris]
        b = [tuple(str(y) for y in x) for x in self.ignore_axioms]
        return f"<{type(self).__name__}: {a}: {b}>"

    def to_uri_identifier( self ):# -> URI_IDENTIFIER:
        return self

    def create_input_generator(self, rdf_graph, uri_subject):
        uri_list = iter(self.find_objects(rdf_graph, uri_subject)).__next__()
        def input_generator(iri_to_pythonobjectcontainers):
            possible_objects: list[list[object]] \
                    = [iri_to_pythonobjectcontainers[x] for x in uri_list]
            #assert all(possible_objects)
            for obj_container_list in it.product( *possible_objects ):
                used_objects = set(it.compress( obj_container_list, \
                        (isinstance(u, rdflib.IdentifiedNode) \
                        for u  in uri_list)))
                object_list = [x.obj for x in obj_container_list]
                #object_list = [x for x in obj_container_list]
                yield object_list, used_objects

        return input_generator

    def find_objects( self, rdf_graph, uri_subject ):
        assert type(uri_subject) in (rdflib.term.URIRef, rdflib.BNode)
        uri_prop = rdflib.term.URIRef( self.uri )
        assert type(uri_prop) in (rdflib.term.URIRef, rdflib.BNode)
        #found_prop_objects = []
        logger.debug( f"search: ({uri_subject}, {uri_prop}, ?)" )
        uris_target = [ x for _,_,x in rdf_graph.triples((uri_subject, uri_prop, None)) ]
        logger.debug( f"found: {uris_target}" )
        yield uris_target

    def find_dependencies( self, rdf_graph, uri_subject):
        return iter(self.find_objects( rdf_graph, uri_subject )).__next__()

@dataclasses.dataclass
class info_attr( constructor_annotation ):
    """Annotated resources will be loaded as single objects.
    Throws error if multiple resources are possible inputs.
    """
    uri: str
    needed: bool = False
    at_generation: bool = False
    inputtype: type = type
    def to_uri_identifier( self ):# -> URI_IDENTIFIER:
        return self

    def create_input_generator(self, rdf_graph, uri_subject):
        node_list = list(self.find_objects(rdf_graph, uri_subject))
        def input_generator(iri_to_pythonobjects):
            for node in node_list:
                try:
                    tmp = iri_to_pythonobjects[ node ]
                except KeyError: #ends if uri has no possible objects
                    continue
                for x in tmp:
                    #yield (x, [x])\
                    yield (x.obj, [x])
        return input_generator

    def __repr__(self):
        name = ".".join((type(self).__module__, type(self).__name__))
        a = "needed" if self.needed else "optional"
        return f"<{name}: {str(self.uri)}: {a}>"

    def __str__(self):
        name = type(self).__name__
        a = "needed" if self.needed else "optional"
        return f"<{name}: {str(self.uri)}: {a}>"

    def find_objects( self, rdf_graph, uri_subject ):
        assert type(uri_subject) in (rdflib.term.URIRef, rdflib.BNode)
        uri_prop = rdflib.term.URIRef( self.uri )
        assert type(uri_prop) in (rdflib.term.URIRef, rdflib.BNode)
        #found_prop_objects = []
        logger.debug( f"search: ({uri_subject}, {uri_prop}, ?)" )
        for _,_,uri_target in rdf_graph.triples((uri_subject, uri_prop, None)):
            logger.debug( f"found: {uri_target}" )
            yield uri_target
            #found_prop_objects.append( uri_target )

    def find_dependencies( self, rdf_graph, uri_subject):
        return list( self.find_objects(rdf_graph, uri_subject))


@dataclasses.dataclass
class info_custom_property( constructor_annotation  ):
    """This class can be used to identify all properties, classified as
    the attribute property_type. It finds to every possible property
    classified as property_type exactly one targeted resource.
    Every used property must be constructed.
    in the example
    .. code::

        <1> [ a <prop> ] <2>
        and if subproperty_of == <prop> then it would find 
        {<constructed_object from [ a <prop>]>: <constructed_object from 2> }

    :TODO: i use a instead of subPropertyOf
    """
    uri: str
    needed = False
    at_generation = False
    inputtype: type = type
    def to_uri_identifier( self ):# -> URI_IDENTIFIER:
        return self

    def __repr__(self):
        name = ".".join((type(self).__module__, type(self).__name__))
        a = "needed" if self.needed else "optional"
        return f"<{name}: {str(self.uri)}: {a}>"

    def __str__(self):
        name = type(self).__name__
        a = "needed" if self.needed else "optional"
        return f"<{name}: {str(self.uri)}: {a}>"

    def create_input_generator(self, rdf_graph, uri_subject):
        node_dict = iter(self.find_objects(rdf_graph, uri_subject)).__next__()
        def input_generator(uri_to_pythonobjects):
            all_uris = set( it.chain( node_dict.keys(), node_dict.values()))
            try:
                for uri_to_obj in _get_combinations(uri_to_pythonobjects, \
                                all_uris):
                    #asd = { uri_to_obj[key]: uri_to_obj[val] \
                    asd = { uri_to_obj[key].obj: uri_to_obj[val].obj \
                            for key, val in node_dict.items() }
                    used_objects = set( uri_to_obj[tmp_uri] \
                            for tmp_uri in it.chain( \
                            node_dict.keys(), \
                            node_dict.values()) \
                            if isinstance( tmp_uri, rdflib.IdentifiedNode))
                    #yield asd, list( it.chain( asd.keys(), asd.values() ))
                    yield asd, used_objects
            except KeyError as err:
                return #im not sure what to do best here
                #because this function returns several possible inputs i
                #feel save just to end this function here instead of
                #doing something else

        return input_generator

    def find_objects( self, rdf_graph, uri_subject: rdflib.IdentifiedNode ):
        # subject_id = "<%s>"%( uri_subject )
        # sparql_search = """SELECT ?prop ?object
        #         WHERE { 
        #             %s ?prop ?object .
        #             ?prop a <%s> .
        #         }
        #         """ %( subject_id, self.uri )
        identifiednodes_to_objecturi = {}
        for _, prop, obj in rdf_graph.triples((uri_subject, None, None)):
            #if (prop, RDF.subPropertyOf, self.uri) in rdf_graph:
            if (prop, RDF.a, self.uri) in rdf_graph:
                identifiednodes_to_objecturi.setdefault(prop, list())\
                                .append( obj )
        q = tuple( identifiednodes_to_objecturi.keys() )
        q2_listlist = [ identifiednodes_to_objecturi[x] for x in q ]
        for q2 in it.product( *q2_listlist ):
            yield { x:q2[i] for i,x in enumerate(q) }

    def find_dependencies( self, rdf_graph, uri_subject):
        needed_nodes = set()
        for _, prop, obj in rdf_graph.triples((uri_subject, None, None)):
            #if (prop, RDF.subPropertyOf, self.uri) in rdf_graph:
            if (prop, RDF.a, self.uri) in rdf_graph:
                needed_nodes.add(prop)
                needed_nodes.add(obj)
        return needed_nodes
        
def _get_combinations( key_to_multiple_values, filter_keys=None ):
    """Yields all different combinations of the values to the keys. Filters 
    for the given keys.

    :type key_to_multiple_values: dict[ Hashable, list[object] ]
    :param key_to_multiple_values:
    :type filter_keys: Container[ Hashable ]
    :param filter_keys: 
    :rtype: dict[ Hashable, object ]
    """
    if filter_keys is None:
        filter_keys = key_to_multiple_values.keys()
    filter_keys = list( filter_keys )
    filter_values = [ key_to_multiple_values[x] for x in filter_keys ]
    for value_array in it.product( *filter_values ):
        yield { key:val for key, val in zip( filter_keys, value_array ) }
