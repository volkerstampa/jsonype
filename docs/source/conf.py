# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
from doctest import ELLIPSIS, NORMALIZE_WHITESPACE

# noinspection PyProtectedMember
from jsonype._version import __version__

sys.path.insert(0, os.path.abspath("../../"))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'jsonype'
# noinspection PyShadowingBuiltins
copyright = '2023, Volker Stampa'
author = 'Volker Stampa'
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme'
]
intersphinx_mapping = {'python': ('https://docs.python.org/', None)}
templates_path = ['_templates']
exclude_patterns = []
show_warning_types = True
# due to TypeVars (see also: https://github.com/sphinx-doc/sphinx/issues/10974)
suppress_warnings = ['ref.class', 'ref.obj']

doctest_default_flags = NORMALIZE_WHITESPACE | ELLIPSIS


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
