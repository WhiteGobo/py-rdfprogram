#!/bin/env python
import argparse

def get_args():
    Programdescription = "Add 1 and save to new file"
    parser = argparse.ArgumentParser( description = Programdescription )
    parser.add_argument( 'loadfile', type=str,
                        help="filepath for loading data" )
    parser.add_argument( 'savefile', type=str,
                        help="filepath for saving data" )

    program_args = parser.parse_args()
    args = ( program_args.loadfile, program_args.savefile )
    return args

def main(loadfile, savefile):
    pass

if __name__=="__main__":
    args = get_args()
    main( *args )
