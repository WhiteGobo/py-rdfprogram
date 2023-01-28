import rdfloader as rl
import rdflib.term
import typing as typ
import urllib
import os.path
import os
import urllib.parse
import subprocess
import sys
import collections as coll
import types
import itertools as it
import logging
logger = logging.getLogger( __name__ )

from . import program_rdf
import importlib.resources
automaton_info_file = importlib.resources.path( program_rdf, 'automaton.ttl' )

Base_automaton = "http://program/automaton#%s"
URI_auto_argument = Base_automaton %( "argument" )
URI_auto_overwritearg = Base_automaton %( "overwrite_argument" )
URI_auto_executable = Base_automaton %( "executable" )
URI_auto_command = Base_automaton %( "command" )
URI_auto_default = rdflib.term.URIRef( Base_automaton %( "default" ) )
URI_auto_defaulttarget = Base_automaton %( "default_target" )
URI_auto_created = rdflib.term.URIRef( Base_automaton %( "created" ) )
URI_auto_uses = Base_automaton %( "uses" )
URI_auto_output = Base_automaton %( "output" )
URI_auto_executes = Base_automaton %( "executes" )
URI_auto_data = Base_automaton %( "data" )
URI_auto_keyword = Base_automaton %( "keyword" )
URI_auto_index = Base_automaton %( "index" )
URI_auto_overwrite = Base_automaton %( "overwrite" )
URI_auto_generates = Base_automaton %( "generates" )
URI_auto_generatabledata = Base_automaton %( "generatabledata" )
_URI_rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def interpolate_newinformation( newfiles_to_placeholder_resources, *rdf_sources ):
    """

    Should be used after calling a program_container. Interpolates new 
    information created by running calling a program_container. Use:
        old_graphs: Iterable[ rdflib.Graph ]
        created_python_objects = rl.load( uri_to_class, *old_graphs )
        foo: program_container
        assert foo in created_python_objects
        ret, new_resources = foo()
        interpolate_newinformation( new_resources, *old_graphs )
        

    :rtype: Iterable[ ( rdflib.term.URIRef, rdflib.term.URIRef, 
                rdflib.term.URIRef) ]
    :returns: A list of new axioms for the generated resources
    """
    g: rdflib.Graph = rl.parse_rdfresources( rdf_sources, {} )
    newaxioms = []
    for newresource, placeholder in newfiles_to_placeholder_resources.items():
        exclude = [ \
                lambda s,p,o: str(p)==_URI_rdf_type and str(s)==placeholder \
                                and str(o)==URI_auto_generatabledata,
                lambda s,p,o: str(p)==URI_auto_generates and str(o)==placeholder,
                ]
        subj = rdflib.term.URIRef( placeholder )
        assert subj in g.subjects(), "placeholder not in Graph"
        newsubj = rdflib.term.URIRef( newresource )
        source,_,_ = it.chain( g.triples( (None, URI_auto_default, newsubj) ),
                    g.triples((None, URI_auto_defaulttarget,newsubj))).__next__()
        newaxioms.append( (source, URI_auto_created, newsubj) )

        #for _, prop, obj in g.triples( (subj,None,None) ):
        #    if any( e(subj,prop,obj) for e in exclude ):
        #        continue
        #    newaxioms.append( (newsubj, prop, obj) )
    return newaxioms


def _find_generatable_properties( rdf_graph ):
    """Finds properties, between data-placeholders.

    :todo: it may be more appropriate to set 'properties' to all connecting
            properties between 2 generatable_data individuums
    """
    automaton_path = "http://program/automaton#"
    URI_generatable_data =rdflib.term.URIRef(f"{automaton_path}generatabledata")
    rdfs_path = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    URI_rdftype = rdflib.term.URIRef(f"{rdfs_path}type")
    generatable_data = { x for x,_,_ in rdf_graph.triples( \
                                    (None, URI_rdftype, URI_generatable_data))}
    properties = { y for _,y,_ in it.chain( \
                *(rdf_graph.triples((r, None, None)) for r in generatable_data), \
                *(rdf_graph.triples((None, None, r)) for r in generatable_data), \
                ) if y != rdflib.term.URIRef('http://program/automaton#generates')}
    return properties


def _util_load_owlonto_from_turtle( filepath, owl_world, onto_base=None ):
    """
    
    :rtype: owl.World
    """
    import tempfile
    import owlready2 as owl
    import os.path
    if onto_base is None:
        onto_base = "file://%s" %( os.path.abspath( filepath ) )
    with tempfile.NamedTemporaryFile( mode="w" ) as tmpfile:
        automaton_baseinfo = rdflib.Graph()
        automaton_baseinfo.parse( filepath )
        with open( tmpfile.name, "w" ) as ff:
            ff.write( automaton_baseinfo.serialize( format="ntriples" ) )
        onto = owl_world.get_ontology( onto_base )
        with open( tmpfile.name, "rb" ) as ff:
            onto.load( fileobj=ff, format="ntriples" )
    return onto


def extend_automaton_axioms_for_transfer( myg:rdflib.Graph ):
    """Gives back the ontology http://program/automaton with extra
    information in the form of swrl-rules. Those new rules, transfer
    properties hold by data-placeholder pointed by arguments to
    the new created data of the useprogram-algorithm

    :todo: Use isolated world of owlready2, see 
        https://owlready2.readthedocs.io/en/latest/world.html
    :todo: im not sure why i have to remove overlap with myg at the end
    :returns: Returns all data from 'http://program/automaton' with extra
            information for transferring properties of argument dataholder
            to newly created resources
    :rtype: rdflib.Graph
    """
    try:
        import owlready2 as owl
    except ModuleNotFoundError as err:
        raise NotImplementedError( "Cant use this method" ) from err
    isolated_world = owl.World()
    try:
        my_onto = iter( isolated_world.ontologies.values() ).__next__()
    except Exception:
        my_onto = isolated_world.get_ontology( "http://anonymous/" )
    URI_automaton = "http://program/automaton#"
    URI_originates = f"{URI_automaton}originates"
    auto_onto = _util_load_owlonto_from_turtle( automaton_info_file, \
                                isolated_world, URI_automaton )
    properties = _find_generatable_properties( myg )
    #automaton_path = "http://program/automaton#"
    #URI_originates = rdflib.term.URIRef( f"{automaton_path}originates" )

    with my_onto:
        #ensure all used properties are registered as objectProperty
        for p in it.chain( properties , (URI_originates,) ):
            myname = urllib.parse.urlsplit( p )[-1]
            base_IRI = p[: -len(myname) ]
            tmp_namespace = my_onto.get_namespace( base_IRI )
            if not getattr( tmp_namespace, myname ):
                with tmp_namespace:
                    types.new_class( myname, (owl.ObjectProperty,) )
        #evaluate new rule for property-transport
        namespace_automaton = my_onto.get_namespace( URI_automaton )
        for p in properties:
            myname = urllib.parse.urlsplit( p )[-1]
            base_IRI = p[: -len(myname) ]
            tmp_namespace = my_onto.get_namespace( base_IRI )
            a = getattr( tmp_namespace, myname )
            rule = owl.Imp()
            assert namespace_automaton[ a.name ] == None, "Ths is a safetyt"\
                        +"hing, because owlready is shitty and cant identify"\
                        +"namespace:resource, cant make inferences for "\
                        +f"{tmp_namespace.name}:{a.name}"
            try:
                newrule = f"originates(?x, ?z), originates(?y,?w),"\
                        + f" {str(a.name)}(?z,?w) -> {str(a.name)}(?x, ?y)"
                rule.set_as_rule( newrule, \
                        namespaces = [ namespace_automaton, tmp_namespace ] )
            except Exception as err:
                raise Exception( "had problems with rule", newrule ) from err
    graph_out = isolated_world.as_rdflib_graph()
    reasoning_graph = rdflib.Graph()
    for axiom in graph_out:
        if axiom not in myg:
            reasoning_graph.add( axiom )
    for name, uri in myg.namespaces():
        reasoning_graph.namespace_manager.bind( name, uri )
    URI_swrl = rdflib.URIRef( "http://www.w3.org/2003/11/swrl#" )
    reasoning_graph.namespace_manager.bind( "swrl", URI_swrl, override=False )
    return reasoning_graph


def _util_rdfgraph_to_owlready_onto( mygraph:rdflib.Graph, world, onto=None ):
    """

    :type onto: owlready2.namespace.Ontology (return of get_ontology)
    :param onto: save data in this ontology
    """
    import tempfile
    import owlready2 as owl
    with tempfile.NamedTemporaryFile() as rdf_information:
        with open( rdf_information.name, "w" ) as qq:
            qq.write( mygraph.serialize( format="ntriples" ) )
        #print( myg.serialize() )
        tmp_onto = world.get_ontology( rdf_information.name )
        tmp_onto.load()
    if onto:
        onto.imported_ontologies.append( tmp_onto )
    return tmp_onto

def helper_reason_over( *graphs: rdflib.Graph, debug=1 ) -> rdflib.Graph:
    """Let a reasoner (Pellet) run over the information of given graphs.
    Returns all new statements. Might have problems with anonymous objects

    :param debug: will be forwarded to owlready2.sync_reasoner_pellet
    """
    try:
        import owlready2 as owl
    except Exception as err:
        raise NotImplementedError( "Cant use this method" )
    wholegraph = rdflib.Graph()
    for g in graphs:
        try:
            for axiom in g:
                wholegraph.add( axiom )
        except Exception as err:
            raise TypeError( f"input {g} seems not to be rdflib.Graph", g ) from err
    g1 = rdflib.compare.to_isomorphic( wholegraph )
    target_onto = _util_rdfgraph_to_owlready_onto( wholegraph, owl.World() )
    #_util_rdfgraph_to_owlready_onto( new_rules, target_onto.world, target_onto )
    owl.sync_reasoner_pellet( target_onto.world, \
                                infer_property_values = True, \
                                infer_data_property_values = False, \
                                debug = debug )

    graph_out = target_onto.world.as_rdflib_graph()
    g2 = rdflib.compare.to_isomorphic( graph_out )
    new_axioms: rdflib.Graph
    old_axioms, q, new_axioms = rdflib.compare.graph_diff( g1, g2 )
    for axiom in new_axioms: #Filter broken anonymous data
        for uri in axiom:
            try:
                uri.n3()
            except Exception:
                new_axioms.remove( axiom )
                continue
    #namespace = { uri: name for name, uri \
            #                            in (x.namespaces() for x in reversed( graphs ))}
    #for uri, name in namespace.items():
    #    new_axioms.namespace_manager.bind( name, uri )
    return new_axioms


class program_attribute:
    @classmethod
    def _init_with_overwrite( cls, uri, \
                    default_value: rl.info_attr( URI_auto_default ) = None,
                    #keyword: rl.info_attr( URI_auto_keyword ) = None,
                    index: rl.info_attr( URI_auto_index ) = None,
                    overwrite: rl.info_attr( URI_auto_overwrite, needed=True ) = None,
                    generates: rl.info_attr( URI_auto_generates ) = None,
                    ):
        return cls( uri, 
                default_value=default_value,
                index=index,
                overwrite=overwrite,
                generates=generates,
                )

    def __init__( self, uri, \
                    default_value: rl.info_attr( URI_auto_default ) = None,
                    keyword: rl.info_attr( URI_auto_keyword ) = None,
                    index: rl.info_attr( URI_auto_index ) = None,
                    overwrite: rl.info_attr( URI_auto_overwrite ) = None,
                    generates: rl.info_attr( URI_auto_generates ) = None,
                    ):
        self.default_value = default_value
        self.uri = uri
        if overwrite is not None:
            self.overwrite = overwrite
        else:
            self.generates = generates
            if keyword is not None:
                self.keyword = keyword
            if index is not None:
                self.index = index

    def _set_generates( self, generates ):
        self._generates = generates
    def _get_generates( self ):
        try:
            return self.overwrite.generates
        except AttributeError:
            return self._generates
    generates = property( fset=_set_generates, fget=_get_generates )

    def _get_keyword( self ):
        try:
            return self.overwrite.keyword
        except AttributeError:
            pass
        return getattr( self, "_keyword", None )
    def _set_keyword( self, keyword ):
        if hasattr( self, "overwrite" ):
            raise Exception( "cant set keyword if has 'overwrite'" )
        self._keyword = keyword
    keyword = property( fget=_get_keyword, fset=_set_keyword )

    def _set_index( self, index ):
        if hasattr( self, "overwrite" ):
            raise Exception( "cant set keyword if has 'overwrite'" )
        self._index = index
    def _get_index( self ):
        try:
            return self.overwrite.index
        except AttributeError:
            pass
        return getattr( self, "_index", None )
    index = property( fget=_get_index, fset=_set_index)

    def _set_defaultvalue( self, default_value ):
        if type( default_value ) in (str, int, float):
            self.datatype = "literal"
            self.__default_value = default_value
        elif type( default_value ) == datafile:
            self.datatype = "file"
            self.__default_value = default_value.filepath
        elif default_value is None:
            self.datatype = ""
            self.__default_value = None
        else:
            raise TypeError( default_value )
    def _get_defaultvalue( self ):
        #try:
        #    q = self.overwrite.default_value
        #except AttributeError:
        #    pass
        return self.__default_value
    default_value = property( fset= _set_defaultvalue, fget=_get_defaultvalue )



class program_container:
    """

    :param attributes: list[ program_attribute ]
    :param executes_program:
    :param program_path:
    :var executes_program: The program_container, from which this program
            origrinates. Is Used for fetching default data
    :todo: remove executes_program as property and instead generate attribute
            when set
    :todo: Attributes arent check, if they are useable by this class
    """
    def __init__( self, uri, \
                attributes: rl.info_attr( URI_auto_uses, is_iter=True )=[], \
                out_attributes: rl.info_attr( URI_auto_output, is_iter=True )=[], \
                executes_program: rl.info_attr( URI_auto_executes ) = None, \
                ):
        self.attributes = attributes
        self.uri = uri
        self.out_attributes = out_attributes

        from urllib.parse import urlparse
        q = urlparse( uri )
        if executes_program:
            self.executes_program = executes_program
        elif q.scheme == "file" and os.path.exists( q.path ):
            self.program_path = q.path
        else:
            raise TypeError( f"{q.path} is no program or need 'executes_program'" )

    def _set_program_path( self, program_path ):
        self._program_path = program_path
    def _get_program_path( self ):
        try:
            return self._program_path
        except AttributeError:
            pass
        if self.executes_program == self:
            raise Exception( "This shouldnt have happened" )
        return self.executes_program.program_path
    program_path: str = property( fget=_get_program_path, \
                    fset=_set_program_path, doc = "Path to the program" )

    def _set_executes_program( self, executes_program ):
        self._executes_program = executes_program
    def _get_executes_program( self ):
        try:
            return self._executes_program
        except AttributeError:
            return self
    executes_program = property( fget=_get_executes_program, \
                                fset=_set_executes_program, \
                                doc="execute the program thingy" )

    def _set_attributes( self, attributes ):
        """

        :todo: Somehow i cant replace cond1 and cond2 with normal if things
        """
        if attributes is None:
            self._attributes = None
            return
        keyword_attr = []
        positional_attr = []
        for attr in attributes:
            key = getattr( attr, "keyword", None )
            if key:
                keyword_attr.append( attr )
            else:
                positional_attr.append( attr )
        if positional_attr:
            cond1 = all( hasattr( x, "index" ) for x in positional_attr )
            try:
                cond2 = max(coll.Counter( x.index for x in positional_attr ).values())>1
            except AttributeError as err:
                raise TypeError() from err
            if not cond1 or cond2:
                raise TypeError( "some attribute doesnt fit" )
            positional_attr.sort( key=lambda x: x.index )
        self._attributes = tuple( positional_attr + keyword_attr )

    def _get_attributes( self ):
        if self.executes_program != self:
            attributes = list( self.executes_program.attributes )
            for overwrite_attribute in self._attributes:
                try:
                    i = attributes.index( overwrite_attribute.overwrite )
                except AttributeError as err:
                    raise Exception( f"something went wrong in {overwrite_attribute}, {overwrite_attribute.uri}") from err
                attributes[ i ] = overwrite_attribute
            return attributes
        else:
            return self._attributes
    attributes: typ.Iterable[ program_attribute ] \
                = property( fget=_get_attributes, fset=_set_attributes,\
                                doc = "my attributes" )

    def _interpolate_program_arguments( self ) -> (list[str], dict[str, str]):
        args = []
        kwargs = {}
        for attr in self.attributes:
            keyword = getattr( attr, "keyword", None )
            val = getattr( attr, "default_value", None )
            if val:
                if keyword:
                    kwargs[ keyword ] = val
                else:
                    args.append( val )
        return args, kwargs

    def __call__( self, skip_reasoning=False ) -> ( str, typ.List[str] ):
        """

        :returns: (return_str, list of new resources) String with 
                the answer of the program and a list of created 
                resources. Resources are named as their respective URI.
        :todo: maybe change the way programpath is fetched
        :todo: maybe replace print with logger
        """
        raise NotImplementedError( "i removed self.ontology_organizer" )
        existing_files = { uri:chk for uri, chk in self._fetch_created_loadable_resources({}) }

        args, kwargs = self._interpolate_program_arguments()
        kwargs_chain = it.chain.from_iterable( kwargs.items() )
        p_args = tuple( str(x) for x in it.chain( args, kwargs_chain ) )

        commandarray = [ str(self.program_path), *(x for x in p_args) ]
        logger.debug( f"Runs terminal command: {commandarray}" )
        q = subprocess.run( commandarray, capture_output=True )
        try:
            q.check_returncode()
            program_return_str = q.stdout.decode()
        except subprocess.CalledProcessError as err:
            print( q.stderr.decode(), file=sys.stderr )
            raise Exception( "failed to execute program" ) from err
        newfiles: list[ str ] = [ url for url,_ \
                    in self._fetch_created_loadable_resources( existing_files )]
        newresources = self._url_to_comparable_rdfterm( newfiles )

        #newresources = tuple( self._fetch_created_axioms( existing_files ) )
        
        new_axioms = interpolate_newinformation( newresources, self.ontology_organizer.rdfgraph.serialize() )
        update_graph = rdflib.Graph()
        for axiom in new_axioms:
            rdflib.Graph()
        try:
            self.ontology_organizer.update_ontology( new_axioms )
        except Exception as err:
            raise Exception( new_axioms ) from err
        if not skip_reasoning:
            new_rules = extend_automaton_axioms_for_transfer( self.ontology_organizer.rdfgraph )
            in_second = helper_reason_over( self.ontology_organizer.rdfgraph, new_rules )
            self.ontology_organizer.update_ontology( in_second )


        return program_return_str, newresources

    def _url_to_comparable_rdfterm( self, urls ):
        """Currently there is a disconnect between a generated resource and
        the information given for the program-execution. The information about
        the newfile is held by a placeholder resource. The information about
        the new generated resource can be derived by the placeholder resource.
        This method gives a map of a resource to its information-placeholder.

        """
        from urllib.parse import urlparse
        asd = {}
        for f in urls:
            q = urlparse( f )
            datatype = q.scheme
            path = q.path
            try:
                attr = ( attr for attr in self.attributes \
                        if attr.datatype == datatype \
                        and attr.default_value == path ).__next__()
            except StopIteration as err:
                raise Exception( f"no attribute to url {f} not found" ) from err
            if attr.generates:
                asd[ f ] = attr.generates.uri
        return asd


    def _fetch_created_loadable_resources( self, existing_files, attributes=None ):
        """Currently only checks for resourcwes not found in existing_files.
        Goes through every argument and checks if resource is now loadable.
        If so, then check if file is new or altered and then yields it.

        :type existing_files: Dict[ Hashable, int ]
        :type attributes: Iterable[ program_attribute ]
        """

        if attributes is None:
            attributes = self.attributes
        #new_subjects = []
        #altered_subjects = []
        for attr in attributes:
            temporary_subject = attr.default_value
            
            #compare program_attribute._set_defaultvalue
            if attr.datatype == "file":
                filepath = temporary_subject
                try:
                    chksum = _get_chksum( filepath )
                    if chksum != existing_files.get( filepath, None ):
                        fileurl = "file://%s" %( filepath )
                        yield fileurl, chksum
                except FileNotFoundError:
                    pass
                #elif _create_chksm( tmp_uri ) != existing_files:
                #    pass
            elif attr.datatype in ("literal", ""):
                pass
            else:
                raise NotImplementedError( type(temporary_subject), attr.datatype )

def _get_chksum( filepath ):
    """Checks if given resource now exists with information

    :todo: write this method
    """
    if os.path.exists( filepath ):
        return os.stat( filepath ).st_mtime
    else:
        raise FileNotFoundError()
    raise Exception( "should never reach here" )
    url = str( rdf_resource )
    if url:
        from urllib.parse import urlparse
        q = urlparse( url )
        if q.scheme == "file":
            if os.path.exists( q.path ):
                return os.stat( q.path ).st_mtime
            else:
                raise FileNotFoundError()
        else:
            raise NotImplementedError( url, rdf_resource )
    else:
        raise NotImplementedError( "_test_if_resource_loadable) cant handle this resource", rdf_resource )


class datafile:
    def __init__( self, filepath ):
        self.filepath = filepath
    @classmethod
    def load_file( cls, url ):
        from urllib.parse import urlparse
        q = urlparse( url )
        if q.scheme == "file":
            return cls( q.path )
        else:
            raise Exception( url )
            os.path.exists( url )
    def _get_url( self ):
        return "file://%s" % (self.filepath)
    url = property( fget=_get_url )

class placeholder:
    def __init__( self, uri, \
                    #connected_info: rl.info_ignoretriples( ((None,URI_auto_generates,None), (None,_URI_rdf_type,URI_auto_generatabledata)) ), \
                    ):
        self.uri = uri


uri_to_class = {
        URI_auto_executable: program_container, 
        URI_auto_command: program_container, 
        URI_auto_argument: program_attribute, 
        URI_auto_overwritearg: program_attribute._init_with_overwrite,
        URI_auto_data: datafile.load_file,
        URI_auto_generatabledata: placeholder,
        }
rdfnode_to_class = { rdflib.URIRef(uri): constructor 
                    for uri, constructor in uri_to_class.items() }
