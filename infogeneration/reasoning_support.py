import owlready2 as owl
import rdflib
import types
import tempfile
import logging
logger = logging.getLogger(__name__)
"""Logger for reasoning"""
import subprocess
import sys
from owlready2.reasoning import _PELLET_CLASSPATH, JAVA_MEMORY
from .pellet_grammar import parse_pelletoutput

def reason_pellet(x, debug=1):
    """Reasoning support. Uses owlready.

    :raises: owl.OwlReadyInconsistentOntologyError
    :raises: owl.OwlReadyJavaError
    """
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as myf:
            myf.write(x.serialize(format="ntriples"))
        #with open(tmp.name, "r") as myf:
        #    print("".join(myf.readlines()))

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
        import time
        logger.debug("Running Pellet...")
        logger.debug(" ".join(command))
        t0 = time.time()

        try:
            output = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, check = True).stdout
        except subprocess.CalledProcessError as e:
            if (e.returncode == 1) and (b"ERROR: Ontology is inconsistent" \
                    in (e.stderr or b"")):
                raise owl.OwlReadyInconsistentOntologyError()
            else:
                raise owl.OwlReadyJavaError("Java error message is:\n%s"\
                        % (e.stderr or e.output or b"").decode("utf8"))

    try:
        output = output.decode("utf8")
    except UnicodeDecodeError:
        output = output.decode("latin")

    logger.debug("Pellet took %s seconds" % (time.time() - t0))
    logger.info("Pellet output: \n%s"%(output))

    return parse_pelletoutput(output)
