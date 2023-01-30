#!/bin/env python
import argparse

def get_args():
    Programdescription = "Sum 2 ints"
    parser = argparse.ArgumentParser( description = Programdescription )
    parser.add_argument( 'first', type=int,
                        help="first integer" )
    parser.add_argument( '--secint', type=int, default=3, 
                        help="second int" )
    parser.add_argument( '--savefile', type=str, default=None,
                        help="filepath for saving data" )
    parser.add_argument( '--placeholder', type=str, default=None,
                        help="target for testresource" )

    program_args = parser.parse_args()
    args = ( program_args.first, program_args.secint )
    kwargs = {}
    if program_args.savefile:
        kwargs["savefile"] = program_args.savefile
    return args, kwargs

def main():
    pass

if __name__=="__main__":
    args, kwargs = get_args()
    main( *args, **kwargs )
