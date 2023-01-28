import rdflib
import rdflib.compare as comp

def main():
    g1 = rdflib.Graph()
    g2 = rdflib.Graph()
    g1.parse( "a.ttl" )
    g2.parse( "b.ttl" )
    cg1 = comp.to_isomorphic( g1 )
    cg2 = comp.to_isomorphic( g2 )
    print(list(cg1 & cg2) )
    a,b,c = comp.graph_diff( cg1, cg2 )
    print( list(a),list(b),list(c) )

    #print( cg1.serialize() )
    #print( list(cg2) )
    #print( cg1 == cg2 )
    return cg1, cg2

if __name__=="__main__":
    main()
