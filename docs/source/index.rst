Welcome to jsonype's documentation!
===================================

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    modules

jsonype is a package for converting Python's
`JSON representation <https://docs.python.org/3/library/json.html#py-to-json-table>`_
to (or from) a Python object of a given
type if possible (i.e. a suitable converter is available).
This is most useful when the given type contains type-hints such that this type-based conversion can be applied
(possibly recursively) for the individual components of the initial type.

Install
-------

Add ``jsonype`` to your dependencies or install with pip::

   pip install jsonype

Usage
-----

Conversion of *standard* types like :func:`dataclasses.dataclass` or :class:`typing.NamedTuple`
works out of the box:

.. literalinclude:: ../../jsonype/typed_json.py
    :dedent:
    :language: python
    :start-after: Example: TypedJson
    :end-before: """

For custom types you can register custom converters:

.. literalinclude:: ../../jsonype/typed_json.py
    :dedent:
    :language: python
    :start-after: Example append:
    :end-before: """

Custom converters can also take precedence over existing ones by prepending:

.. literalinclude:: ../../jsonype/typed_json.py
    :dedent:
    :language: python
    :start-after: Example prepend:
    :end-before: """

See :class:`jsonype.TypedJson` for more details on the API.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
