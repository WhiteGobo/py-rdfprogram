#!/bin/env python
import argparse
import rdflib
import pathlib

def get_args():
    Programdescription = "Prints number in file as axiom:\n"\
            "\t{loadfile}[ <http://info#value> ] = Value_in_File"
    parser = argparse.ArgumentParser( description = Programdescription )
    parser.add_argument( 'loadfile', type=str,
                        help="filepath for loading data" )

    program_args = parser.parse_args()
    args = ( program_args.loadfile, )
    return args

def main(loadfile):
    with open(loadfile, "r") as file:
        lines = file.readlines()
    assert len(lines) == 1
    try:
        q = int(lines[0])
    except ValueError as err_int:
        try:
            q = float(lines[0])
        except ValueError as err_float:
            raise Exception("Not a number: %s"%(lines)) from err_float

    g = rdflib.Graph()
    node_file = rdflib.URIRef(pathlib.Path(loadfile).as_uri())
    value_prop = rdflib.URIRef("http://info#value")
    g.add((node_file, value_prop, rdflib.Literal(q)))
    print(g.serialize())

if __name__=="__main__":
    args = get_args()
    main( *args )
