from base64 import b64decode, b64encode
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit
from uuid import UUID

from jsonype.basic_from_json_converters import (FromJsonConverter,
                                                FunctionBasedFromSimpleJsonConverter)
from jsonype.basic_to_json_converters import FunctionBasedToSimpleJsonConverter, ToJsonConverter


# mimic class name
# noinspection PyPep8Naming
def ToPath() -> FromJsonConverter[Path, None]:  # noqa: N802
    """Return a converter that converts a JSON string to a :class:`pathlib.Path`.

    The JSON string is expected to be in a format parseable by :class:`pathlib.Path`,
    otherwise the conversion raises a :class:`FromJsonConversionError`
    """
    return FunctionBasedFromSimpleJsonConverter(Path, str, Path)


# mimic class name
# noinspection PyPep8Naming
def FromPath() -> ToJsonConverter[Path]:  # noqa: N802
    """Return a converter that converts objects of type :class:`pathlib.Path`.

    A ``Path`` is converted to a string using ``str``.
    """
    # correct according to mypy
    # noinspection PyTypeChecker
    return FunctionBasedToSimpleJsonConverter[Path](str, Path)


# mimic class name
# noinspection PyPep8Naming
def ToUUID() -> FromJsonConverter[UUID, None]:  # noqa: N802
    """Return a converter that converts a JSON string to a :class:`uuid.UUID`.

    The JSON string is expected to be in a format parseable by :class:`uuid.UUID`,
    otherwise the conversion raises a :class:`FromJsonConversionError`
    """
    return FunctionBasedFromSimpleJsonConverter(UUID, str, UUID)


# mimic class name
# noinspection PyPep8Naming
def FromUUID() -> ToJsonConverter[UUID]:  # noqa: N802
    """Return a converter that converts objects of type :class:`uuid.UUID`.

    An ``UUID`` is converted to its 8-4-4-4-12 format using ``str``.
    """
    # correct according to mypy
    # noinspection PyTypeChecker
    return FunctionBasedToSimpleJsonConverter[UUID](str, UUID)


# mimic class name
# noinspection PyPep8Naming
def ToBytes() -> FromJsonConverter[bytes, None]:  # noqa: N802
    """Return a converter that converts a JSON string to :class:`bytes`.

    The JSON string is expected to be in a base64 encoded string
    otherwise the conversion raises a :class:`FromJsonConversionError`.
    """
    return FunctionBasedFromSimpleJsonConverter(b64decode, str, bytes)


# mimic class name
# noinspection PyPep8Naming
def FromBytes() -> ToJsonConverter[bytes]:  # noqa: N802
    """Return a converter that converts objects of type :class:`bytes`.

    ``bytes`` are converted to a base64 encoded string.
    """
    def bytes_to_str(bs: bytes) -> str:
        return b64encode(bs).decode("ascii")
    return FunctionBasedToSimpleJsonConverter[bytes](bytes_to_str)


# mimic class name
# noinspection PyPep8Naming
def ToUrl() -> FromJsonConverter[SplitResult, None]:  # noqa: N802
    """Return a converter that converts a JSON string to :class:`urllib.parse.SplitResult`.

    The JSON string is expected to be a URL that can be parsed with :func:`urllib.parse.urlsplit`
    otherwise the conversion raises a :class:`FromJsonConversionError`.
    """
    return FunctionBasedFromSimpleJsonConverter(urlsplit, str, SplitResult)


# mimic class name
# noinspection PyPep8Naming
def FromUrl() -> ToJsonConverter[SplitResult]:  # noqa: N802
    """Return a converter that converts objects of type :class:`urllib.parse.SplitResult`.

    A ``SplitResult`` is converted by :func:`urllib.parse.urlunsplit`.
    """
    return FunctionBasedToSimpleJsonConverter[SplitResult](urlunsplit, SplitResult)
