import owlready2 as owl
import rdflib
import types
import tempfile
import subprocess
import sys
from owlready2.reasoning import _PELLET_CLASSPATH, JAVA_MEMORY

def reason_pellet(x, debug=1):
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as myf:
            myf.write(x.serialize(format="ntriples"))

        # Use Jena for loading because OWLAPI is bugged with NTriples.
        command = [owl.JAVA_EXE, 
                   "-Xmx%sM" % JAVA_MEMORY,
                   "-cp", _PELLET_CLASSPATH,
                   "pellet.Pellet",
                   "realize",
                   #"--loader", "Jena", #jena isnt able to load BNodes correct
                   "--input-format", "N-Triples",
                   "--ignore-imports",
                   "--infer-prop-values",
                   "--infer-data-prop-values",
                   tmp.name]
        if debug:
            import time
            print("* Owlready2 * Running Pellet...", file = sys.stderr)
            print("    %s" % " ".join(command), file = sys.stderr)
            t0 = time.time()

        try:
            output = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, check = True).stdout
        except subprocess.CalledProcessError as e:
            if (e.returncode == 1) and (b"ERROR: Ontology is inconsistent" in (e.stderr or b"")): # XXX
                raise OwlReadyInconsistentOntologyError()
            else:
                raise OwlReadyJavaError("Java error message is:\n%s" % (e.stderr or e.output or b"").decode("utf8"))

        try:
            output = output.decode("utf8").replace("\r","")
        except UnicodeDecodeError:
            output = output.decode("latin").replace("\r","")

        if debug:
            print("* Owlready2 * Pellet took %s seconds" % (time.time() - t0), file = sys.stderr)
        if debug > 1:
            print("* Owlready2 * Pellet output:", file = sys.stderr)
            print(output, file = sys.stderr)

        print("\n\nMyoutput:\n")
        print(output)
        raise Exception(output)
        new_parents = defaultdict(list)
        new_equivs  = defaultdict(list)
        entity_2_type = {}
        stack = []
        for line in output.split("\n"):
            if not line: continue
            line2 = line.lstrip()
            depth = len(line) - len(line2)
            splitted = line2.split(" - ", 1)
            class_storids = [ontology._abbreviate(class_iri) for class_iri in splitted[0].split(" = ")]

            if len(class_storids) > 1:
                for class_storid1 in class_storids:
                    for class_storid2 in class_storids:
                        if not class_storid1 is class_storid2:
                            new_equivs[class_storid1].append(class_storid2)

            while stack and (stack[-1][0] >= depth): del stack[-1]
            if len(stack) > 1: # if len(stack) == 1, it only contains Thing => not interesting
                for class_storid in class_storids:
                    entity_2_type[class_storid] = "class"
                    new_parents[class_storid].extend(stack[-1][1])
            else:
                for class_storid in class_storids:
                    entity_2_type[class_storid] = "class"
            stack.append((depth, class_storids))

            if len(splitted) == 2:
                ind_iris = splitted[1][1:-1].split(", ")
                for ind_iri in ind_iris:
                    ind_storid = ontology._abbreviate(ind_iri)
                    entity_2_type[ind_storid] = "individual"
                    new_parents[ind_storid].extend(class_storids)

        if infer_property_values:
            inferred_obj_relations = []
            for a_iri, prop_iri, b_iri in _PELLET_PROP_REGEXP.findall(output):
                prop = world[prop_iri]
                if prop is None: continue
                a_storid = ontology._abbreviate(a_iri, False)
                b_storid = ontology._abbreviate(b_iri.strip(), False)
                if ((not a_storid is None) and (not b_storid is None) and
                    (not world._has_obj_triple_spo(a_storid, prop.storid, b_storid)) and
                    ((not prop._inverse_property) or (not world._has_obj_triple_spo(b_storid, prop._inverse_storid, a_storid)))):
                    inferred_obj_relations.append((a_storid, prop, b_storid))


        if infer_data_property_values:
            inferred_data_relations = []
            for a_iri, prop_iri, value, lang, datatype in _PELLET_DATA_PROP_REGEXP.findall(output):
                prop = world[prop_iri]
                if prop is None: continue
                a_storid = ontology._abbreviate(a_iri, False)
                if lang and (lang != "()"):
                    datatype = "@%s" % lang
                else:
                    datatype = ontology._abbreviate(datatype)
                    python_datatype = owlready2.base._universal_abbrev_2_datatype.get(datatype)
                    if   python_datatype is int:   value = int  (value)
                    elif python_datatype is float: value = float(value)
                if ((not a_storid is None) and
                    (not world._has_data_triple_spod(a_storid, prop.storid, value))):
                    inferred_data_relations.append((a_storid, prop, value, datatype))
