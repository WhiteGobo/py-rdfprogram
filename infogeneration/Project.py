from . import tactic

from rdfloader import extension_classes as extc
from . import namespaces
import importlib.resources
autgen_path = importlib.resources.files(namespaces).joinpath("autgen2.ttl")

from rdfloader.rdf_namespace import rdf_namespace
AUTGEN = rdf_namespace.from_file(autgen_path, namespace="http://example.com/automaticgenerator#", format="ttl")


#program_path = importlib.resources.files(test_src).joinpath( "myprogram.py" )
#program_uri = rdflib.URIRef(pathlib.Path(program_path).as_uri())
#rdf_namespace.from_file()


class project:
    """Implements a tactic for a certain target
    """
    def __init__(self, uri, uses: extc.info_attr(AUTGEN.implements),
                 target_information: extc.info_attr_list(AUTGEN.target)):
        pass


input_dict = {AUTGEN.project: project}
