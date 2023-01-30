"""Loader for rdf classes from rdflib-compatible files. 
Loads given uris as with given constructor. Automaticly loads also subclasses.
Constructors should correspond to given knowledgegraph_constructor"""
import rdflib
import itertools as it
import collections.abc
import dataclasses
import logging
logger = logging.getLogger( __name__ )
from urllib import parse as up
import os.path
import traceback
from .classloader import ObjectfromUri_generator as _ObjectfromUri_generator
import abc
import typing as typ
from .classloader import MissingPreUri, SkipAllCreation, MultipleUrisToSingleAttribute, MissingNeededUris

#from .extension_classes import info_attr, info_ignoretriples, info_uriinvert, info_custom_property, info_attr_list

#####################################################################
#some custom typings
import typing as typ
Uri = str

from . import RDF


#####################################################################
#constants
_rdf_prefix = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_rdfs_prefix = "http://www.w3.org/2000/01/rdf-schema#"
#@prefix owl: <http://www.w3.org/2002/07/owl#> .

URI_rdfs_subclass = rdflib.term.URIRef( "".join((_rdfs_prefix, "subClassOf")))
URI_rdfs_subproperty = rdflib.term.URIRef( "".join((_rdfs_prefix, "subPropertyOf")))
URI_type = rdflib.term.URIRef( "".join((_rdf_prefix, "type")))

#####################################################################
#dataclasses used for packing information and objects

@dataclasses.dataclass( frozen=True )
class _complex:
    """Used for identifying python object constructed by algorithm.
    """
    uri: rdflib.IdentifiedNode
    constructor: typ.Callable
    helpconst: _ObjectfromUri_generator
    #def __post_init__( self ):
    #    object.__setattr__( self, "uri", str( self.uri ) )
    def __eq__( self, other ):
        return all((
                self.uri == other.uri,
                self.constructor == other.constructor
                ))
    def __hash__( self ):
        return hash((self.uri, self.constructor))

@dataclasses.dataclass
class _object_wrapper:
    obj: object
    construct: _complex
    helpconst: object # same as construct.helpconst
    needed_attributes: list = None
    further_needed_attributes: list = None
    addable: list[ (str, Uri) ] = None
    added_attributes: dict[ str, list ] = None
    used_objects: set = None

#####################################################################
#methods and classes
myConstructor = typ.Callable
"""This is a describption of the constructors

"""

def load_from_graph( uri_to_constructor, rdf_graph, wanted_resources=None ):
    """Loads all IRIs in wanted_resources from the knowledgegraph described
    by rdf_graph as python-objects. The resources are depending on 
    uri_to_constructor loaded as python-objects. 

    :type uri_to_constructor: Dict[ rdflib.URIRef, Callable ]
    :param uri_to_constructor: A mapping of a resource class to a constructor.
            All resources from the knowledgegraph classified as given resource
            will be loaded as described in the constructor. Classification
            is specified by rdf:type 'a' or \"http://www.w3.org/1999/02/22-rdf-syntax-ns#type\".
    :type rdf_graph: rdflib.Graph
    :param rdf_graph: Knowledgegraph from which the resources will be loaded.
    :type wanted_resources: Iterable[ rdflib.IdentifiedNode ]
    :param wanted_resources: All Resources that ought to be loaded.
            Resources must be described by the knowledgegraph. If no
            wanted_resources are given, tries to load every available Resource
    :TODO: new objects from _get_creationinfo should be a eindeutige form
    """
    if not hasattr( rdf_graph, "all_nodes" ):
        raise TypeError( "rdf_graph expected rdflib.Graph, got", rdf_graph )
    if wanted_resources is None:
        wanted_resources = set( filter( \
                                lambda x: isinstance(x, rdflib.URIRef) \
                                and x not in uri_to_constructor, \
                                rdf_graph.subjects() ) )
    else:
        wanted_resources = [ x if isinstance( x, rdflib.IdentifiedNode ) \
                                else rdflib.URIRef(x) \
                                for x in wanted_resources ]
    starting_wanted_resources = list(wanted_resources)

    assert all( isinstance( x, rdflib.IdentifiedNode) \
                                for x in wanted_resources ), wanted_resources
    assert all( isinstance(x, rdflib.IdentifiedNode ) \
                                for x in uri_to_constructor )
    wanted_resources = list( set(wanted_resources) )

    uri_to_construct: typ.Dict = {}
    construct_with_attr_to_uri: typ.Dict = {}
    old_constructed_complexes = []

    missing_resources = [ x for x in wanted_resources \
                                if x not in rdf_graph.all_nodes()]
    assert not missing_resources, f"missing resources: {missing_resources}"
    logger.debug( f"starting wanted resources: {wanted_resources}" )
    for uri_resource in wanted_resources: #will be extended in runtime
        logger.debug( f"find information to {uri_resource}" )
        for constructor, attr_to_uri, helpconst, new_objects \
                                in _get_creationinfo_to( uri_resource, \
                                rdf_graph, uri_to_constructor ):
            construct_id = _complex( uri_resource, constructor, helpconst )
            uri_to_construct.setdefault( uri_resource, []).append(construct_id)
            construct_with_attr_to_uri[ construct_id ] = attr_to_uri
            #Here is a todo: new_objects should have a eindeutige form
            for x in new_objects:
                if isinstance( x, rdflib.IdentifiedNode ):
                    if x not in wanted_resources:
                        logger.debug( f"new wanted resource: {x}")
                        wanted_resources.append( x )
                elif isinstance( x, list ):
                    for y in x:
                        if y not in wanted_resources:
                            wanted_resources.append( y )
                elif isinstance( x, rdflib.Literal):
                    pass
                else:
                    raise Exception( x )

    #logger.debug( "Needed but not generatable: %s"% ( 
    #                _find_needed_but_not_generatable_resources( \
    #                uri_to_construct, construct_with_attr_to_uri )))
    logger.debug( f"wanted resources: {wanted_resources}" )

    
    constructlist: list[_complex] = list( construct_with_attr_to_uri.keys() )
    logger.debug( "create all objects" )
    object_wrapper_list: list[_object_wrapper] = _create_all_objects( 
                            constructlist, {}, \
                            uri_to_construct, construct_with_attr_to_uri )
    logger.debug( "start removing not valid objects" )

    object_wrapper_list = _remove_incomplete_objects( object_wrapper_list )
    asdf = {}
    for x in object_wrapper_list:
        assert isinstance( x.construct.uri, rdflib.IdentifiedNode ), type(x.construct.uri)
        asdf.setdefault( x.construct.uri, list() ).append( x.obj )
    
    missing_wanted_resources = [x for x in starting_wanted_resources 
                                if x not in asdf ]
    if missing_wanted_resources:
        logger.warning(f"missing wanted resources: %s"
                       %([str(x) for x in missing_wanted_resources]))
        #logger.warning("further needed resources of the algorithm: %s"
        #               %([str(x) for x in wanted_resources if x not in asdf 
        #                  and x not in missing_wanted_resources]) )
    return asdf

def _get_creationinfo_to( target_resource, g: rdflib.Graph, \
                        uri_to_constructor: typ.Dict[ str, typ.Callable ] ):
    """

    :returns: For each differentiable generatable construct, this method
            yields:
                - URI
                - constructor-method
                - attributename of the constructor and the generated 
                    object to used URIs
    :rtype: Iterator[ (uri, callable, list[uri], list[uri], dict[ str, uri ] ) ]
    """
    assert isinstance( target_resource, (str, rdflib.URIRef) )
    for _,_,x in g.triples((target_resource, RDF.a, None)):
        logger.debug( f"find to {target_resource} the type {x}" )
        try:
            constructor = uri_to_constructor[x]
        except KeyError:
            logger.warning( f"skip {target_resource} cause no constructor to type {x}" )
            continue
        infoobject = _ObjectfromUri_generator.from_class_constructor( \
                                                            constructor )
        infoobject.process_argument_info( target_resource, g )
        pre = infoobject.pre_needed_attributes
        post = infoobject.post_needed_attributes
        attr_to_uri = infoobject.attr_to_uri
        missing = tuple(filter( lambda x: x not in attr_to_uri, \
                                it.chain( pre, post )))
        if missing:
            logger.info( f"skip {target_resource} with {constructor} "
                            f"cause missing input for attribute {missing}" )
            continue
        new_objects = infoobject.possible_dependencies
        #new_objects = list(attr_to_uri.values())
        assert all( isinstance( x, (rdflib.IdentifiedNode, rdflib.Literal) ) for x in new_objects ), new_objects
        yield constructor, attr_to_uri, infoobject, new_objects



def _find_needed_but_not_generatable_resources( uri_to_construct, \
                                                construct_with_attr_to_uri, ):
    raise NotImplementedError("Seems to not work anymore")
    all_generatable_objects = set( x.uri for x \
                        in it.chain.from_iterable( uri_to_construct.values()))
    logger.debug( "List of all used constructs: %s" %(all_generatable_objects))
    dependencies = [ y \
                        for y in it.chain.from_iterable( x.values() \
                        for x in construct_with_attr_to_uri.values()
                        ) if type(y) != rdflib.term.Literal ]
    all_single_dependencies = set( it.chain.from_iterable( \
                                [x] if type(x) == rdflib.term.URIRef \
                                else x for x in dependencies ) )
    needed_but_not_generatable = [str(i) for i in all_single_dependencies \
                                if str(i) not in all_generatable_objects ]
    return needed_but_not_generatable


def parse_rdfresources(rdf_sources, uri_to_constructor, execute_reasoner=None)\
        -> rdflib.Graph:
    """

    :todo: I have implemented a bad workaround with hastattr(...,"uri") 
            at reason_resource_has_property
    """
    g = rdflib.Graph()
    for s in rdf_sources:
        try:
            if up.urlparse( str(s) ).scheme != '' or os.path.exists( s ):
                g.parse( s )
            else:
                g.parse( data=s )
        except Exception as err2:
            raise KeyError( ("%.60s doesnt seem to be rdflib-compatible" \
                            "resource. complete: %s") % (s,s)) from err2

    if execute_reasoner:
        g = execute_reasoner( g )

    for uri_main in uri_to_constructor.keys():
        g = reason_whatis_class( uri_main, g )

    for uri_main, constructor in uri_to_constructor.items():
        w = _ObjectfromUri_generator.from_class_constructor( constructor )\
                .attr_from_uri
        for info_wrapper in w.values():
            uri_prop = info_wrapper.uri
            g = reason_resource_has_property( uri_main, uri_prop, g )

    return g


def reason_resource_has_property( uri_main, uri_prop, rdf_graph ):
    logger.debug( "reason_resource_has_property not implemented" )
    return rdf_graph

def reason_whatis_class( uri_main, rdf_graph ):
    logger.debug( "reason_whatis_class not implemented" )
    return rdf_graph




def _get_creationinfo( g: rdflib.Graph, \
                        uri_to_constructor: typ.Dict[ str, typ.Callable ],\
                        old_constructed_complexes: list[ _complex ] = []):
    """

    :returns: For each differentiable generatable construct, this method
            yields:
                - URI
                - constructor-method
                - pre-initializaion needed other URIs
                - post-initialization needed other URIs
                - attributename of the constructor and the generated 
                    object to used URIs
    :rtype: Iterable[ (uri, callable, list[uri], list[uri], dict[ str, uri ] )]
    """
    raise Exception()
    get_all_of_type = lambda x: ( uri_resource for uri_resource,_,_ \
                        in g.triples((None, URI_type, rdflib.term.URIRef( x))))
    for uri_main, constructor in uri_to_constructor.items():
        for uri_resource in get_all_of_type( uri_main ):
            if _complex(uri_resource,constructor) in old_constructed_complexes:
                continue
            try:
                infoobject = _ObjectfromUri_generator.from_class_constructor( \
                                                                constructor)
                attr_to_uri =infoobject.process_argument_info( uri_resource, g)
                pre = infoobject.pre_needed_attributes
                post = infoobject.post_needed_attributes
                missing = tuple(filter( lambda x: x not in attr_to_uri, \
                                        it.chain( pre, post )))
                if missing:
                    logger.info( f"missing Uris {missing} to {uri_resource} "\
                                    f"with {constructor}" )
                    continue
            #        raise MissingNeededUris( missing )
            #except MissingNeededUris as err:
            #    logger.info( f"missing Uris {err.missing} to {uri_resource} "\
            #                   f"with {constructor}" )
            #    continue
            except MultipleUrisToSingleAttribute as err:
                logger.warning( f"multiple property-uris {err.attribute}: "\
                                f"{err.found_properties} found to "\
                                f"{uri_resource} with {constructor}" )
                continue
            yield uri_resource, constructor, pre, post, attr_to_uri


class _urimapper( collections.abc.MutableMapping ):
    """Saves to every uri a list of objects

    :todo: remove __setitem__ and instead create lists, when getitem is used
    """
    def __init__( self, old_dictionary=None ):
        container = {}
        for uri, object_list in old_dictionary.items():
            newlist = list( object_list )
            container[ uri ] = newlist
        self.container = container

    def remove_objects( self, *objects ):
        """remove target obejcts from list in urimapper"""
        self.container = { a:[ x for x in b if x not in objects ] for a,b in self.container.items() }
        self.container = { a:b for a,b in self.container.items() if len(b)>0 }

    def contains_object( self, target ):
        all_objects = list( it.chain.from_iterable( self.container.values() ) )
        if target in all_objects:
            return True
        elif type( target ) in ( int, str ):
            return True
        else:
            try:
                all_entries_contained = all( self.contains_object( x ) \
                                                for x in target )
            except Exception as err:
                all_entries_contained = False
            return all_entries_contained
        #    if all_entries_contained:
        #        return True
        #return False

    def __getitem__( self, uri ):
        struri = str( uri )
        if struri in self.container:
            return self.container[ struri ]
        elif type( uri ) == rdflib.term.Literal:
            return [ uri.toPython() ]
        elif type( uri ) in ( list, tuple ):
            urilist = uri
            missing = [ tmpuri for tmpuri in urilist if tmpuri in self.container ]
            if missing:
                raise KeyError( f"missing uris {missing}" )
            return it.product( *(self.__getitem__( tmpuri ) \
                                    for tmpuri in urilist ))
        else:
            raise KeyError( uri )

    def __iter__( self ):
        return iter( self.container )

    def __len__( self ):
        return len( self.container )

    def __setitem__( self, uri, item ):
        if type(uri) == rdflib.term.Literal:
            return
        uri = str( uri )
        self.container[ uri ] = item
    def __delitem__( self, uri ):
        uri = str( uri )
        return self.container.__delitem__( uri )

    def __repr__( self ):
        return f"<{type(self)}: {self.container}>"

    def __str__( self ):
        return f"urimapper({self.container})"
Uri_str = str


def _create_all_objects( constructlist: list[_complex], \
                        uri_to_pythonobjects: dict[Uri, typ.List], \
                        uri_to_construct, construct_with_attr_to_uri ):
    """

    :param constructlist: this determines, which object should be created
    :type constructlist: list[ _complex ]
    :rtype List[ _object_wrapper ]
    :returns: List of wrappers for created objects from resources
    :todo: somewhy removing addable breaks, if break at the end of this 
            method is removed. That shouldnt be the case
    """
    uri_to_pythonobjects = _urimapper( uri_to_pythonobjects )

    #construct_with_attr_to_uri = dict( construct_with_attr_to_uri )
    done_something = True
    object_wrapper_list: typ.List[_object_wrapper] = []
    #obj_to_needed_attributes = {}
    #obj_to_addable = {}
    #logger.debug( f"try to create following things: {constructlist}" )
    while done_something and constructlist:
        done_something = False
        logger.debug( f"repeat {constructlist}" )
        for construct in constructlist:
            #uri_object, constructor = construct
            uri_object = construct.uri
            constructor = construct.constructor
            helpconst = construct.helpconst
            tmp_attr_to_uri = construct_with_attr_to_uri[ construct ]
            logger.debug( F"Try creating {construct.uri}" )
            try:
                newobj, added_attr, used_objects = helpconst.create_object( \
                                    uri_to_pythonobjects )
            except (MissingPreUri, SkipAllCreation) as err:
                #logger.debug( f"skipped, cause: {sys.exc_info()[0]} with " \
                #                   f"description: {sys.exc_info()[1]}" )
                logger.debug( f"skipped, cause: {traceback.format_exc()}" )
                continue
            tmp_container = _object_wrapper( newobj, construct, helpconst )
            tmp_container.needed_attributes = tuple( filter( \
                                    lambda x: x not in added_attr, \
                                    tmp_attr_to_uri.keys() ))
            if tmp_container.needed_attributes:
                logger.debug( f"further needed attributes: %s" \
                        %({ a:tmp_attr_to_uri[a] \
                        for a in tmp_container.needed_attributes}) )
            tmp_container.added_attributes = dict( added_attr )
            tmp_container.used_objects = used_objects
            tmp_container.further_needed_attributes = [ attr \
                        for attr in tmp_container.needed_attributes \
                        if attr not in tmp_container.added_attributes ]
            tmp_container.addable = [ (attr, uri) \
                                    for attr, uri in tmp_attr_to_uri.items() \
                                    if attr not in added_attr ]
            uri_to_pythonobjects.setdefault( uri_object,[]).append( newobj )
            constructlist.remove( construct )
            done_something = True
            object_wrapper_list.append( tmp_container )
            logger.debug( f"Created {newobj}" )
            logger.debug( f"Yet Created: {list(uri_to_pythonobjects)}" )
    
        #for newobj in it.chain.from_iterable( uri_to_pythonobjects.values() ):
        for tmp_container in object_wrapper_list:
            newobj = tmp_container.obj
            for x in tmp_container.addable:
                attr, attr_uri = x
                for val, object_list in tmp_container.helpconst.attr_to_inputgenerator[attr](uri_to_pythonobjects):
                    try:
                        setattr( newobj, attr, val )
                        logger.debug( f"for {newobj} set attribute "\
                                        f"'{attr}' with '{val}'.")
                    except TypeError as err:
                        logger.debug( f"skipped setting attribute "\
                                        f"'{attr}' with '{val}'. "\
                                        f"Cause: '{repr(err)}'")
                        continue
                    tmp_container.added_attributes[ attr ] = val
                    tmp_container.addable.remove( x )
                    tmp_container.used_objects.update( object_list )
                    tmp_container.further_needed_attributes.remove( attr )
                    done_something = True
                    break
    return object_wrapper_list



def _remove_incomplete_objects( object_wrapperlist ):
    """Removes not completed objects from object_wrapperlist

    :type uri_to_pythonobjects: _urimapper
    :type object_wrapperlist: list[ _object_wrapper ]
    """
    object_wrapperlist = list( object_wrapperlist )

    need_repetition = True
    for x in object_wrapperlist:
        if x.further_needed_attributes:
            logger.info( f"removes {x.construct} because no " \
                            "valid input for following attributes: %s" \
                            % (x.further_needed_attributes) )
    object_wrapperlist = [x for x in object_wrapperlist \
                            if not x.further_needed_attributes ]
    #new_wrapperlist = []
    #for tmp_wrapper in object_wrapperlist:
    #    missing_object_for_attributes \
    #            = [ attr for attr in tmp_wrapper.needed_attributes \
    #                if attr not in tmp_wrapper.added_attributes ]
    #    if missing_object_for_attributes:
    #        logger.info( f"removes {tmp_wrapper.construct} because no " \
    #                    "valid input for following attributes: %s" \
    #                    %( [ attr for attr in tmp_wrapper.needed_attributes \
    #                    if attr not in tmp_wrapper.added_attributes ]) )
    #    else:
    #        new_wrapperlist.append( tmp_wrapper )
    #object_wrapperlist = new_wrapperlist
    for _ in range( len(object_wrapperlist) ): #ensures maximal runtime
        need_repetition = False
        all_objects = [ w.obj for w in object_wrapperlist ]
        for tmp_wrapper in tuple( object_wrapperlist ):
            logger.debug( f"{tmp_wrapper}, {all_objects}" )
            if not all( x in all_objects for x in tmp_wrapper.used_objects ):
                missing = [x for x in tmp_wrapper.used_objects \
                                    if x not in all_objects ]
                logger.debug( f"remove {tmp_wrapper.construct} because"
                                f"missing used objects: {missing}" ) 
                object_wrapperlist.remove( tmp_wrapper )
                need_repetition = True
                all_objects = [ w.obj for w in object_wrapperlist ]
        if not need_repetition:
            break
    return object_wrapperlist
