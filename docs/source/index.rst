Welcome to json-t's documentation!
==================================

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    modules

json-t is a package for converting Python's
`JSON representation <https://docs.python.org/3/library/json.html#py-to-json-table>`_
to (or from) a Python object of a given
type if possible (i.e. a suitable converter is available).
This is most useful when the given type contains type-hints such that this type-based conversion can be applied
(possibly recursively) for the individual components of the initial type.

Getting Started
---------------

Add ``json-t`` to your dependencies or install with pip::

   pip install json-t

For details on how to use it see :class:`jsont.typed_json.TypedJson`.



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
