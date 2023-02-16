import logging
logger = logging.getLogger(__name__)

from . import classloader as cl
import typing as typ
import rdflib
from . import RDF
import itertools as it
import traceback
import abc
from . import ontology_updater

class FailedCreation(Exception):
    """Is thrown, when an expected Error is thrown, while creating an object
    """
    pass

class SkippedEveryInput(Exception):
    """Is thrown, when adding all input via set to object, an input is skipped.
    """
    pass

class SkippedSomeInput(Exception):
    """Is thrown, when adding all input via set to object, an input is skipped.
    """
    pass

class abc_creator(abc.ABC):
    obj: object
    """Generated object"""
    possible_dependencies: typ.List
    """All other resources(iris) which should be available to create the object
    """

    @abc.abstractmethod
    def create_object(self, iri_to_objectcontainers):
        pass
    @abc.abstractmethod
    def add_all_input_resources(self, uri_to_objects) -> bool:
        """Checks if available resources can be added and returns if all
        needed resources are added.

        :param iri_to_objectcontainers: All objects currently construct as 
            mapping of a iri to an object_container.
        :type iri_to_objectcontainers: dict[iri, typ.List[object_creator]]
        :raises SkippedInput: Is thrown, when some attr couldnt be assigned
            the required objects.
        :TODO: change val to a pythonobject directly instead of using the 
            container
        """
        pass

    @abc.abstractmethod
    def dependent_on_objects(self, objectcreator_list) -> bool:
        """Checks if contained object is dependent on any object in
        one container of the given list.

        :param iri_to_objectcontainers: A list of object_containers
            for which the dependency is checked.
        :type iri_to_objectcontainers: typ.List[object_creator]
        :returns: if self.obj is dependent on any object of any
            of the given object_containers
        """
        pass

class object_holder(abc_creator):
    possible_dependencies = []
    def __init__(self, iri, obj):
        self.iri = iri
        self.uri_main = iri
        self.obj = obj

    def dependent_on_objects(self, objectcreator_list):
        return False

    def create_object(self, iri_to_objectcontainers):
        pass

    def add_all_input_resources(self, uri_to_objects):
        return

class literal_creator(abc_creator):
    possible_dependencies = []
    def __init__(self, iri):
        assert isinstance(iri, rdflib.Literal)
        self.uri_main = iri
        self.obj = self.uri_main.toPython()

    def __repr__(self):
        name = type(self).__name__
        ad = repr(self.uri_main)
        return f"<{name}:{ad}>"

    def dependent_on_objects(self, objectcreator_list):
        return False

    def create_object(self, iri_to_objectcontainers):
        pass

    def add_all_input_resources(self, uri_to_objects):
        return

class object_creator(cl.ObjectfromUri_generator, abc_creator):
    """Contains all information for rdf_loader.load_from_graph

    :TODO: Maybe its better not this to be a child of cl.asdf . Instead one
        could cloud all the information and methods within cl.asdf and 
        let this class instead hold an instance of cl.asdf
    """
    obj: object
    """Generated object"""
    dependencies: typ.List
    """List of other object_creators, that hold resources used as input
    for self.obj
    """
    needed_attributes: list = None
    further_needed_attributes: list = None
    addable: list[ (str, rdflib.IdentifiedNode) ] = None
    added_attributes: dict[ str, list ] = None
    """I dont think i want this attribute anymore. Selfexplaining"""
    attr_to_inputgenerator: dict[str, typ.Callable]

    used_objects: set = None
    """List of dependencies of self.obj. points to object_container of the 
    class object_creator
    """

    def create_object(self, iri_to_objectcontainers):
        """Create object from constructor and the given objects

        :param iri_to_objectcontainers: All objects currently construct as 
            mapping of a iri to an object_container.
        :type iri_to_objectcontainers: dict[iri, typ.List[object_creator]]
        :raises FailedCreation: If failing because missing resources, this
            exception will be raised
        """
        #uri_to_pythonobjects = { key:[x.obj for x in valuelist] for key, valuelist in iri_to_objectcontainers.items() }
        assert not any(getattr(self, x, None) for x in ("obj", \
                "needed_attributes", "addable", "added_attributes", \
                "used_objects"))
        uri_object = self.uri_main
        constructor = self

        #this should make no sense, because there should per constructor only
        #be one generated object
        tmp_attr_to_uri = self.attr_to_uri

        logger.debug( F"Try creating {self.uri_main}" )
        try:
            self.obj, added_attr, used_objects = super().create_object( \
                                iri_to_objectcontainers )
        except (cl.MissingPreUri, cl.SkipAllCreation) as err:
            #logger.debug( f"skipped, cause: {sys.exc_info()[0]} with " \
            #                   f"description: {sys.exc_info()[1]}" )
            logger.debug( f"skipped, cause: {traceback.format_exc()}" )
            logger.debug
            raise FailedCreation() from err
        self.needed_attributes = tuple( filter( \
                                lambda x: x not in added_attr, \
                                tmp_attr_to_uri.keys() ))
        if self.needed_attributes:
            logger.debug( f"further needed attributes: %s" \
                    %({ a:tmp_attr_to_uri[a] \
                    for a in self.needed_attributes}))
        self.added_attributes = dict( added_attr )
        self.used_objects = used_objects
        self.further_needed_attributes = [ attr \
                    for attr in self.needed_attributes \
                    if attr not in self.added_attributes ]
        self.addable = [ attr for attr, uri in tmp_attr_to_uri.items() \
                                if attr not in added_attr ]

        logger.debug( f"Created {self.obj}" )
        #uri_to_pythonobjects.setdefault( uri_object,[]).append( newobj )
        #logger.debug( f"Yet Created: {list(uri_to_pythonobjects)}" )

    def add_all_input_resources(self, uri_to_objects) -> bool:
        """Checks if available resources can be added and returns if all
        needed resources are added.

        :param iri_to_objectcontainers: All objects currently construct as 
            mapping of a iri to an object_container.
        :type iri_to_objectcontainers: dict[iri, typ.List[object_creator]]
        :raises SkippedInput: Is thrown, when some attr couldnt be assigned
            the required objects.
        :TODO: change val to a pythonobject directly instead of using the 
            container
        """
        dependencylist: typ.List[object_creator]
        val: object_creator
        attr: str
        done_something = False

        for attr in list(self.addable):
            logger.debug(f"try adding to {attr}")
            for val, dependencylist in self.attr_to_inputgenerator[attr](uri_to_objects):
                try:
                    setattr(self.obj, attr, val )
                    logger.debug( f"for {self.obj} set attribute "\
                                    f"'{attr}' with '{val}'.")
                except TypeError as err:
                    logger.debug( f"skipped setting attribute "\
                                    f"'{attr}' with '{val}'. "\
                                    f"Cause: '{repr(err)}'")
                    continue
                #self.added_attributes[attr] = val
                #tmp_container.added_attributes[ attr ] = val
                self.addable.remove(attr)
                self.used_objects.update(dependencylist)
                self.further_needed_attributes.remove(attr)
                done_something = True
                break
        if self.addable and done_something:
            raise SkippedSomeInput()
        elif self.addable:
            raise SkippedEveryInput()

    def dependent_on_objects(self, objectcreator_list):
        """Checks if contained object is dependent on any object in
        one container of the given list.

        :param iri_to_objectcontainers: A list of object_containers
            for which the dependency is checked.
        :type iri_to_objectcontainers: typ.List[object_creator]
        :returns: if self.obj is dependent on any object of any
            of the given object_containers
        """
        return any( x in self.used_objects for x in objectcreator_list )


def _create_all_objects(constructlist: typ.List[object_creator], \
        already_constructed:dict[rdflib.IdentifiedNode, list])\
        -> dict[rdflib.IdentifiedNode, list]:
    """

    :param constructlist: List of all available constructs
    :return: Mapping of IRIs to a list of generated objects
    """
    done_something = True
    constructlist = list(constructlist)
    iri_to_objectcontainers = {iri: [object_holder(iri, x) for x in objects] 
                               for iri, objects in already_constructed.items()}
    to_add_something = []
    while done_something and (constructlist or to_add_something):
        logger.debug( f"still trying to create following: {constructlist}")
        done_something = False
        for generator in tuple(constructlist):
            try:
                generator.create_object(iri_to_objectcontainers)
            except FailedCreation:
                continue
            logger.debug(f"Created {generator.uri_main}")
            constructlist.remove(generator)
            iri_to_objectcontainers.setdefault(generator.uri_main, []).append(generator)
            to_add_something.append(generator)
            done_something = True
        for generator in tuple(to_add_something):
            logger.debug(f"Adding all missing to {generator}")
            try:
                generator.add_all_input_resources(iri_to_objectcontainers)
            except SkippedEveryInput:
                logger.debug("couldnt add any needed")
                continue
            except SkippedSomeInput:
                logger.debug("skipped inputs")
                done_something = True
                continue
            logger.debug( f"everything added")
            to_add_something.remove(generator)
            done_something = True
    logger.debug( f"All created: {iri_to_objectcontainers}" )
    ret = []
    deleted = []
    logger.debug(f"deleting {to_add_something} for missing dependencies")
    for mylist in iri_to_objectcontainers.values():
        for generator in mylist:
            if generator not in to_add_something:
                ret.append(generator)
            else:
                deleted.append(generator)
    done_something=True
    while done_something:
        done_something=False
        for generator in list(ret):
            if generator.dependent_on_objects(deleted):
                deleted.append(generator)
                ret.remove(generator)
                done_something = True
                logger.debug(f"got dependency issue with {generator}")
    iri_to_pythonobject = {}
    for generator in ret:
        iri_to_pythonobject.setdefault(generator.uri_main, []).append(generator.obj)
    return iri_to_pythonobject



def _type_control_load_from_graph(uri_to_constructor, rdf_graph, wanted_resources):
    if not hasattr( rdf_graph, "all_nodes" ):
        raise TypeError( "rdf_graph expected rdflib.Graph, got", rdf_graph )
    starting_wanted_resources = list(wanted_resources)
    assert all( isinstance(x, rdflib.IdentifiedNode) for x in wanted_resources)

    assert all( isinstance( x, rdflib.IdentifiedNode) \
                                for x in wanted_resources ), wanted_resources
    assert all( isinstance(x, rdflib.IdentifiedNode ) \
                                for x in uri_to_constructor )
    missing_resources = [ x for x in wanted_resources \
                                if x not in rdf_graph.all_nodes()]
    assert not missing_resources, f"missing resources: {missing_resources}"

def load_from_graph( uri_to_constructor, rdf_graph, wanted_resources=None,
                    iri_to_pythonobjects: dict[rdflib.IdentifiedNode, list]={}):
    """Loads all IRIs in wanted_resources from the knowledgegraph described
    by rdf_graph as python-objects. The resources are depending on 
    uri_to_constructor loaded as python-objects. 

    :param iri_to_pythonobjects: Already build old objects. Will be reused and
            also reiterated in returned dict
    :type iri_to_pythonobjects: dict[rdflib.IdentifiedNode, object]
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

    :returns: mapping of uris to list of objects. Filters literals out.
    :TODO: new objects from _get_creationinfo should be a eindeutige form
    """
    if wanted_resources is None:
        wanted_resources = set( filter( \
                                lambda x: isinstance(x, rdflib.URIRef) \
                                and x not in uri_to_constructor, \
                                set(rdf_graph.subjects()) ) )
    wanted_resources = list( set(wanted_resources) )
    _type_control_load_from_graph(uri_to_constructor, rdf_graph, wanted_resources)

    tmp = rdflib.Graph()
    for ax in rdf_graph:
        tmp.add(ax)
    rdf_graph = tmp
    for ax in ontology_updater.reason_update(rdf_graph):
        rdf_graph.add(ax)

    logger.debug( f"starting wanted resources: {wanted_resources}" )

    constructlist: typ.List[objectcreator] = []
    for uri_resource in wanted_resources: #will be extended in runtime
        logger.debug(f"find information to {uri_resource}")
        for infoobject in _get_creationinfo_to(uri_resource, \
                                rdf_graph, uri_to_constructor, \
                                iri_to_pythonobjects):
            logger.debug(f"new constructor: {infoobject}")
            constructlist.append(infoobject)
            new_objects = infoobject.possible_dependencies
            for x in new_objects:
                if isinstance( x, rdflib.IdentifiedNode ):
                    if x not in wanted_resources:
                        logger.debug( f"new wanted resource: {x}")
                        wanted_resources.append( x )
                elif isinstance( x, list ):
                    raise NotImplementedError("Im not sure when this happens")
                    for y in x:
                        if y not in wanted_resources:
                            logger.debug( f"new wanted resource: {x}")
                            wanted_resources.append( y )
                elif isinstance( x, rdflib.Literal):
                    if x not in wanted_resources:
                        logger.debug( f"new wanted resource: {x}")
                        wanted_resources.append( x )
                else:
                    raise Exception("this should never happen",x)
    logger.debug( f"Create all objects {constructlist}" )
    
    return_dict = _create_all_objects(constructlist, iri_to_pythonobjects)
    return { key:values for key, values in return_dict.items()
            if isinstance(key, rdflib.IdentifiedNode)}


def _get_creationinfo_to(target_resource, g: rdflib.Graph, 
                         uri_to_constructor: typ.Dict[str, typ.Callable],
                         already_existing_resources):
    """

    :returns: For each differentiable generatable construct, this method
            yields:
                - URI
                - constructor-method
                - attributename of the constructor and the generated 
                    object to used URIs
    :rtype: Iterator[(uri, callable, list[uri], list[uri], dict[str, uri])]
    """
    if isinstance(target_resource, rdflib.Literal):
        yield literal_creator(target_resource)
        return
    assert isinstance( target_resource, (rdflib.URIRef, rdflib.BNode) )
    for _,_,x in g.triples((target_resource, RDF.a, None)):
        try:
            constructor = uri_to_constructor[x]
        except KeyError:
            logger.warning(f"skip at {target_resource} the type {x}, cause no constructor")
            continue
        logger.debug(f"Create via {constructor}")
        infoobject = object_creator.from_class_constructor(constructor)
        try:
            infoobject.process_argument_info(target_resource, g)
        except cl.MissingPrerequisites as err:
            if any(x not in already_existing_resources for x in err.args[0]):
                logger.info(f"skipped cause: {err.args}")
                continue
        yield infoobject
