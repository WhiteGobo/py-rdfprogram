# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'automatic-generation-pathfinder'
copyright = '2022, Richard Focke Fechner'
author = 'Richard Focke Fechner'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os, sys
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(1, os.path.abspath('../../../'))
from lin_flowgraph_abstract import *
from lin_flowgraph_abstract import flowgraph
import lin_flowgraph_abstract

extensions = [
        'sphinx.ext.autodoc',
        #'sphinx.ext.autosectionlabel',
        #'sphinx.ext.doctest',
        #'sphinx.ext.extlinks',
        #'sphinx.ext.intersphinx',
        #'sphinx.ext.graphviz',
        'sphinx.ext.todo',
]

templates_path = ['_templates']
exclude_patterns = []

# should do, that every todo from sourcecode is implemented in ..todolist::
todo_include_todos = True




# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
