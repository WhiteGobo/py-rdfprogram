from . import AUTGEN
from rdfloader import extension_classes as extc

class tactic:
    def __init__(self, iri, uses: extc.info_attr_list(AUTGEN.uses)):
        raise NotImplementedError()
