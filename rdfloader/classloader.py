"""In this module are many different methods, that are used in support 
of the main methods

"""
import inspect
import logging
logger = logging.getLogger( __name__ )
import rdflib
import abc
import typing as typ
import itertools as it
import traceback
from .extension_classes import constructor_annotation

class MultipleUrisToSingleAttribute( Exception ):
    """Is thrown, when to an attribute multiple references are found

    :TODO: Im not sure if this is needed any longer
    """
    def __init__( self, attribute, found_properties ):
        super().__init__( attribute, found_properties )
        self.attribute = attribute
        self.found_properties = found_properties

class MissingNeededUris( Exception ):
    def __init__( self, missing, *args ):
        super().__init__( missing, *args )
        self.missing = missing
class SkipAllCreation( Exception ):
    pass

class MissingPreUri( KeyError ):
    """Cant create a single object because a pre-creation needed 
    uri is missing
    """
    def __init__( self, preuri, *args, **kwargs ):
        super().__init__( preuri, *args, **kwargs )


class argument_processor:
    attr_from_uri: typ.Final[ typ.Dict[ str, constructor_annotation ] ]

    uri_main: str
    attr_to_uri: typ.Dict[str, object]
    possible_dependencies: list[ rdflib.IdentifiedNode ]
    pre_needed_resources: typ.Final[ set[ rdflib.IdentifiedNode ] ]


    def process_argument_info( self, uri_main, rdf_graph ):
        """Returns a dictionary that maps the arguments of constructor
        to a list of URI, which are used as input
        Changes self.uri_main and self.attr_to_uri
        self.possible_dependencies
        self.pre_needed_resources

        :todo: remove as described in code
        :todo: write logging for unused axioms
        :todo: rewrite typecontrol to assertion instead
        """
        if not all( hasattr(x, "find_objects") \
                for x in self.attr_from_uri.values()):
            raise TypeError( f"The annotations for the "
                        f"constructor for {uri_main} arent compatible to "
                        f"{constructor_annotation}" )
        self.uri_main = uri_main
        logger.debug( f"Process: {uri_main}" )
        all_objects = {}
        for _, p, o in rdf_graph.triples((uri_main, None, None)):
            all_objects.setdefault( o, [] ).append(p)
        self.possible_dependencies = set()
        self.pre_needed_resources = set()
        self.attr_to_uri = {}
        self.attr_to_inputgenerator = {}

        for attr, uri_prop in self.attr_from_uri.items():
            try:
                self.attr_to_inputgenerator[attr] \
                        = uri_prop.create_input_generator(rdf_graph, uri_main)
                assert self.attr_to_inputgenerator[attr] is not None
            except StopIteration:
                pass



        attr: str
        uri_prop: constructor_annotation
        for attr, uri_prop in self.attr_from_uri.items():
            found_prop_objects = list( uri_prop.find_objects( \
                                                rdf_graph, uri_main ))
            logger.debug( f"found_prop_objects: {found_prop_objects}" )
            if len( found_prop_objects ) == 1:
                self.attr_to_uri[ attr ] = found_prop_objects[0]
            elif len( found_prop_objects ) > 1:
                raise MultipleUrisToSingleAttribute( attr, found_prop_objects )

        for attr, uri_prop in self.attr_from_uri.items():
            asf = uri_prop.find_dependencies(rdf_graph, uri_main)
            self.possible_dependencies.update(asf)
            if attr in self.pre_needed_attributes:
                self.pre_needed_resources.update(asf)
        return self.attr_to_uri


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

class info_from_class_constructor:
    """Implements Class generator from_class_constructor as classmethod."""
    attr_from_uri: typ.Dict[str, constructor_annotation]
    """dictionary of attributename to constructor_annotation to search for"""
    pre_needed_attributes: typ.List[str]
    """all needed attributes, before calling the class_constructor"""
    post_needed_attributes: typ.List
    """all needed attributes, which are to be used as inputattribute or 
    to be assigned per
    >> obj.attribute = something
    """
    optional_attributes: typ.List
    """all attributes, that can be assigned per
    >> obj.attribute = something
    """
    class_constructor: typ.Callable
    """method to create object"""
    attr_to_inputgenerator: typ.Dict[str, typ.Callable[typ.Dict,typ.Iterable]]

    def __init__( self, attr_from_uri, \
            pre_needed_attributes, \
            post_needed_attributes, \
            optional_attributes, \
            class_constructor, \
            ):
        self.attr_from_uri = attr_from_uri
        self.pre_needed_attributes = pre_needed_attributes
        self.post_needed_attributes = post_needed_attributes
        self.optional_attributes = optional_attributes
        self.class_constructor = class_constructor


    @classmethod
    def from_class_constructor( cls, class_constructor:constructor_annotation):
        """This method uses the annotations of the given class_constructor
        to generate information on where and how to search for the needed
        input. This method doesnt look up information from any rdf-source.

        :todo: i shouldnt use obj.uri, or i dont know why it is here anyway.
            typicly i use obj.to_uri_identifier to return obj itself.
        """
        from inspect import Parameter as P
        pre_needed_attributes = []
        post_needed_attributes = []
        optional_attributes = []
        sig = inspect.signature( class_constructor )

        if type( class_constructor ) == type:
            constructor_annotations = inspect.get_annotations( \
                                                    class_constructor.__init__)
        else:
            constructor_annotations =inspect.get_annotations(class_constructor)
        attr_to_annotation = { attr: (anno.to_uri_identifier() \
                        if hasattr(anno, "to_uri_identifier")\
                        else rdflib.term.URIRef(anno.uri) )\
                        for attr, anno in constructor_annotations.items() }
        assert all( hasattr( uritransformer, "find_objects" ) \
                        for uritransformer in attr_to_annotation.values() ), \
                        attr_to_annotation
        needed_token = [attr for attr, anno in constructor_annotations.items()\
                            if anno.needed ]
        is_preneeded = lambda x: x.default == inspect._empty \
                        and x.kind \
                        in (P.POSITIONAL_ONLY, P.POSITIONAL_OR_KEYWORD)
        valid_post = lambda x: x.default != inspect._empty \
                        and x.kind \
                        in (P.POSITIONAL_ONLY, P.POSITIONAL_OR_KEYWORD, \
                        P.KEYWORD_ONLY)
        attr_and_info_iter = iter( sig.parameters.items() )
        try:
            attr1, _ = attr_and_info_iter.__next__()
            #attr2, _ = attr_and_info_iter.__next__() #filters ontology
        except StopIteration as err:
            raise TypeError( f"Given constructor {class_constructor} doesnt "
                            "comply to Uri_to_python_constructor" ) from err
        for attr, info in attr_and_info_iter:
            #logger.debug( str( (attr, info, info.kind) ) )
            if is_preneeded( info ):
                #logger.debug( f"{attr} is pre_needed_attribute" )
                pre_needed_attributes.append( attr )
            elif valid_post( info ):
                #if attr in class_constructor.needed:
                if attr in needed_token:
                    #logger.debug( f"{attr} is post_needed_attribute" )
                    post_needed_attributes.append( attr )
                else:
                    #logger.debug( f"{attr} is optional" )
                    optional_attributes.append( attr )
            elif info.kind in ( inspect.Parameter.VAR_KEYWORD,
                            inspect.Parameter.VAR_POSITIONAL ):
                logger.debug( f"ignoring attribute {attr} of "\
                            f"{class_constructor}. See "\
                            f"{knowledgegraph_constructor} for further "\
                            "information" )

        return cls( attr_to_annotation, \
                pre_needed_attributes, \
                post_needed_attributes, \
                optional_attributes, \
                class_constructor )

class ObjectfromUri_generator(argument_processor, info_from_class_constructor):
    pre_needed_attributes: typ.Final[ str ]
    pre_needed_resources: typ.Final[ set[ rdflib.IdentifiedNode ] ]
    post_needed_attributes: typ.Final[ str ]
    #optional_attributes: typ.Final[str]
    uri_main: typ.Final[ rdflib.IdentifiedNode ]
    class_constructor: typ.Final[ typ.Callable ]
    get_possible_inputs_for_argument: typ.Callable[ \
                                    (rdflib.IdentifiedNode, typ.Dict ) ]

    def create_object( self, uri_to_pythonobjects ):
        if not all( uri in uri_to_pythonobjects 
                   for uri in self.pre_needed_resources ):
            raise MissingPreUri( [ uri for uri in self.pre_needed_resources 
                                    if uri not in uri_to_pythonobjects ] )

        #for attr in self.pre_needed_attributes:
        #    if self.attr_to_uri[ attr ] not in uri_to_pythonobjects:
        #        raise MissingPreUri( self.attr_to_uri[attr] )

        pres = self.pre_needed_attributes
        posts = [ x for x in self.post_needed_attributes \
                if self.attr_to_uri[ x ] in uri_to_pythonobjects ]

        def asdf( input_arguments: list ):
            tmp1 = {}
            for arg in input_arguments:
                tmp1[arg] = tuple(self.attr_to_inputgenerator[arg]\
                                    (uri_to_pythonobjects))
                #tmp1[ arg ] = tuple( self.get_possible_inputs_for_argument( \
                        #                    arg, uri_to_pythonobjects ) )

            qwer = it.product( *(tmp1[x] for x in input_arguments) )
            for tmp_single_arg in qwer:
                used_objects = set()
                arg_to_input = {}
                for arg, tmp in zip( input_arguments, tmp_single_arg ):
                    single_input, list_of_objects = tmp
                    arg_to_input[ arg ] = single_input
                    used_objects.update( list_of_objects )
                yield arg_to_input, used_objects

        for r in range( len( posts ), -1, -1 ):
            for q in it.permutations( posts, r=r ):
                input_arguments = list( it.chain( pres, q ) )
                #Workaround if input_arguments==[]:
                try:
                    tmp2 = list(asdf( input_arguments )) 
                    #        if input_arguments else [[]]
                except IndexError: #seems to be a relict
                    continue
                                
                for myinput, used_objects in tmp2:
                    try:
                        newobj = self.class_constructor( self.uri_main, \
                                                        **myinput )
                    except TypeError as err:
                        logger.debug( "".join(traceback.format_exception(err)))
                        continue
                    except Exception as err:
                        raise
                        raise Exception( myinput, input_objects, input_arguments, [arg_to_input(x) \
                                    for x in input_arguments] ) from err
                    return newobj, dict( myinput ), set(used_objects)
        raise SkipAllCreation(pres, posts, uri_to_pythonobjects)


    def _create_object_old( self, uri_to_pythonobjects ):
        """This used to call the constructor

        :type uri_object: str
        :type constructor: Callable
        :type attr_to_uri: Dict[ str, str ]
        :type pres: tuple[ uriref ]
        :param pres: pre_init_dependencies
        :type posts: tuple[ uriref ]
        :param posts: postinit_dependencies
        :type uri_to_pythonobjects: urimapper
        """
        logger.debug( f"try create {self.uri_main} with {self.class_constructor}" )
        pres = self.pre_needed_attributes
        posts = self.post_needed_attributes
        #logger.debug( f"try create {uri_object}} with {constructor}" )
        try:
            pre_inputs = [ uri_to_pythonobjects[self.attr_to_uri[attr]] \
                                        for attr in pres ]
        except KeyError as err:
            raise MissingPreUri( *err.args ) from err
        #logger.debug( f"to {construct} found input {p}")
        try:
            posts_inputs = { attr:uri_to_pythonobjects[self.attr_to_uri[attr]]\
                                        for attr in posts \
                                        if self.attr_to_uri[attr] \
                                        in uri_to_pythonobjects }
        except KeyError as err:
            raise MissingPreUri( *err.args ) from err

        extras = { attr:uri for attr, uri in self.attr_to_uri.items() \
                        if uri in uri_to_pythonobjects and attr not in pres }
        extra_args = tuple( it.chain.from_iterable( (\
                        ( (attr, obj) for obj in uri_to_pythonobjects[uri] )\
                        for attr, uri in extras.items() )))
        assert all( posts_inputs[posts.index(x)] == y for x, y in posts )
        logger.debug( f"has extra args for: {extras}" )

        used_inputtypes = []
        for inputobjects in it.product( *pre_inputs ):
            #for r in range( len( posts ), -1, -1 ):
            #    for q in it.permutations( posts_inputs, r=r ):

            for r in range( len( extra_args ), -1, -1 ):
                for q in it.permutations( extra_args, r=r ):
                    attr_to_obj = { a:b for a,b in zip(pres, inputobjects) }
                    for a,b in q:
                        attr_to_obj[a] = b
                    logger.debug( f"try input {attr_to_obj}" )
                    try:
                        newobj = self.class_constructor( self.uri_main, \
                                                        **attr_to_obj )
                    except TypeError as err:
                        tmp_intypes = { attr:type( obj ) for attr, obj \
                                            in attr_to_obj.items() }
                        if tmp_intypes not in used_inputtypes:
                            logger.warning( f"failed to create {self.uri_main}"
                                            f"with {constructor} via "
                                            f"{tmp_intypes}" )
                            used_inputtypes.append( tmp_intypes )
                        logger.debug( "".join(traceback.format_exception( err )) )
                        continue
                    return newobj,  dict( attr_to_obj )
        raise SkipAllCreation()

def _dict_permutations_to( mydict: typ.Dict[ object, typ.Iterable[object]],\
                                keys = None )\
                                -> typ.Iterator[typ.Dict[ object, object]]:
    if keys:
        keys = list( mydict.keys() )
    else:
        keys = list( keys )
    value_permutations = [ mydict[x] for x in keys ]
    for tmp_values in it.product( value_permuatations ):
        yield { k:v for k,v in it.zip( keys, tmp_values ) }
