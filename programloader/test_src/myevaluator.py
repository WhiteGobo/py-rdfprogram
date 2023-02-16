#!/bin/env python
import argparse
import rdflib
import pathlib

def get_args():
    Programdescription = "Load number inside of the file"
    parser = argparse.ArgumentParser( description = Programdescription )
    parser.add_argument( 'loadfile', type=str,
                        help="filepath for loading data" )

    program_args = parser.parse_args()
    args = ( program_args.loadfile, )
    return args

def main(loadfile):
    with open(loadfile, "r") as myf:
        firstline = myf.readline()
        assert myf.read() == ''
    mynumber = float(firstline)
    if mynumber.is_integer:
        mynumber = int(mynumber)

    g = rdflib.Graph()
    g.add((
        rdflib.URIRef(pathlib.Path(loadfile).as_uri()),
        rdflib.URIRef("http://example.com/containsNumber"),
        rdflib.Literal(mynumber)
        ))
    print(g.serialize())

if __name__=="__main__":
    args = get_args()
    main( *args )
