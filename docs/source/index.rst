.. jsont documentation master file, created by
   sphinx-quickstart on Sun Mar 26 17:11:27 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to jsont's documentation!
=================================

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    modules

jsont is a package for converting Python's
`JSON representation <https://docs.python.org/3/library/json.html#py-to-json-table>`_
to (or from) a Python object of a given
type if possible (i.e. a suitable converter is available).
This is most useful when the given type contains type-hints such that this type-based conversion can be applied
(possibly recursively) for the individual components of the initial type.

Getting Started
---------------

Add ``jsont`` to your dependencies or install with pip::

   pip install jsont

For details on how to use it see :class:`jsont.typed_json.TypedJson`.



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
