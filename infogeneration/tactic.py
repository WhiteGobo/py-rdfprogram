from . import AUTGEN
from rdfloader import extension_classes as extc
import programloader

class tactic:
    uses: programloader.program
    def __init__(self, iri, uses: extc.info_attr_list(AUTGEN.uses)):
        self._typecontrol_uses(uses)
        self.uses = uses

    @classmethod
    def _typecontrol_uses(cls, uses):
        myProgram.example_nodes
        myProgram.generated_nodes
        myProgram.old_axioms
        myProgram.new_axioms

