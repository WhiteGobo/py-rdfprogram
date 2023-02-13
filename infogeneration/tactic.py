from . import AUTGEN
from rdfloader import extension_classes as extc
import programloader

class tactic:
    uses: programloader.program
    """all availagle programs which are used, by this tactic"""
    def __init__(self, uri, uses: extc.info_attr_list(AUTGEN.uses)):
        self.uri = uri
        self._typecontrol_uses(uses)
        self.uses = uses

    @classmethod
    def _typecontrol_uses(cls, uses: list[programloader.program]):
        for p in uses:
            try:
                p.example_nodes
                p.generated_nodes
                p.old_axioms
                p.new_axioms
            except AttributeError as err:
                raise TypeError("must all be programloader.program") from err

