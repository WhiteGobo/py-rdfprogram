import ply.lex as lex
import ply.yacc as yacc
import rdflib
import logging
logger = logging.getLogger(__name__)
"""Logger for grammar"""
from programloader import RDF_NS as _RDF

tokens = (
        "PROPINST",
        "DATAPROPVAL",
        "IRI",
        "BNODE",
        "LITERALSTART",
        "LITERALMIDDLE",
        "RPAREN",
        "STR",
        "BOOL",
        "FLOAT",
        "INT",
        "LPAREN",
        "HYPHEN",
        "COMMA",
        )


t_PROPINST = r"PROPINST:"
t_DATAPROPVAL = r"DATAPROPVAL:"
t_LITERALSTART = r"literal\("
t_LITERALMIDDLE = r"\,\(\)\,"
t_RPAREN = r"\)"
t_LPAREN = r"\("
t_HYPHEN = r"\-"
t_COMMA = r","

def t_BNODE(t):
    r"[a-zA-Z]+:[a-zA-Z/][a-zA-Z0-9_/:.#-]*_:[a-zA-Z0-9_/:.#]+"
    t.value = rdflib.BNode(str(t.value).split("_:")[-1])
    return t

def t_IRI(t):
    r"[a-zA-Z]+://[a-zA-Z/][a-zA-Z0-9_/:.#]*"
    t.value = rdflib.URIRef(t.value)
    return t

def t_STR(t):
    r"'.*?'"
    t.value = t[1:-1]
    return t

def t_BOOL(t):
    r"(false|False|FALSE|TRUE|true|True)"
    if t.value.lower() == "true":
        t.value = True
    elif t.value.lower() == "false":
        t.value = False
    else:
        raise TypeError(t)
    return t

def t_FLOAT(t):
    r"[0-9]*\.[0-9]+"
    t.value = float(t.value)
    return t

def t_INT(t):
    r"[0-9]+"
    t.value = int(t.value)
    return t

def t_error(t):
    raise Exception(t, t.lexer.lineno)

def t_ignore_newline(t):
    r'[\n\r]+'
    t.lexer.lineno += t.value.count('\n') + t.value.count('\n')

t_ignore = ' \t'

lexer = lex.lex()

def p_main(p):
    """main : classifications axioms"""
    p[0] = p[1] + p[2]

def p_classifications_dupl(p):
    """classifications : classifications classifications"""
    p[0] = p[1] + p[2]

def p_classifications(p):
    """classifications : term HYPHEN LPAREN terms RPAREN"""
    p[0] = [(subj, _RDF.a, p[1]) for subj in p[4]]

def p_terms(p):
    """terms : term COMMA terms"""
    p[0] = [p[1]] + p[3]

def p_terms_cutoff(p):
    """terms : term"""
    p[0] = [p[1]]

def p_axioms(p):
    """axioms : axiom axioms"""
    p[0] = [p[1]] + p[2]

def p_axioms_cutoff(p):
    """axioms : """
    p[0] = []

def p_axiom(p):
    """axiom : axiomtype term term term"""
    p[0] = (p[2], p[3], p[4])

def p_term(p):
    """term : IRI
            | BNODE
            | literal"""
    p[0] = p[1]

def p_axiomtype(p):
    """axiomtype : PROPINST
                  | DATAPROPVAL"""
    p[0] = p[1]

def p_literal(p):
    """literal : LITERALSTART value LITERALMIDDLE IRI RPAREN"""
    p[0] = rdflib.Literal(p[2], datatype=p[4])

def p_value(p):
    """value : STR
            | BOOL
            | FLOAT
            | INT"""
    p[0] = p[1]


def p_error(p):
    raise Exception(p)

parser = yacc.yacc(errorlog=logger)

def parse_pelletoutput(data):
    parser.error = 0
    ast = parser.parse(data)
    return ast
