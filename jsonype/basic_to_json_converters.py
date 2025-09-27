from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from inspect import Parameter, signature
from typing import Any, Callable, Generic, TypeVar, get_args

from jsonype.base_types import Json, JsonNull, JsonSimple

SourceType_contra = TypeVar("SourceType_contra", contravariant=True)
JsonType_co = TypeVar("JsonType_co", bound=JsonSimple, covariant=True)


class ToJsonConversionError(ValueError):
    def __init__(self, o: Any, reason: str | None = None) -> None:
        super().__init__(f"Cannot convert {o} to JSON {f': {reason}' if reason else ''}")


class UnsupportedSourceTypeError(ValueError):
    def __init__(self, o: Any) -> None:
        super().__init__(f"Converting objects of type {type(o)} to JSON not supported")


class ToJsonConverter(ABC, Generic[SourceType_contra]):
    """The base-class for converters that convert to objects representing JSON.

    Converters that convert objects of their specific type ``T`` to objects representing JSON have
    to implement the two abstract methods defined in this base-class.

    SourceType_contra:
        The type of the object that shall be converted into an object representing JSON.
    """

    @abstractmethod
    def can_convert(self, o: Any) -> bool:
        """Return if this converter can convert the given object to an object representing JSON.

        Args:
            o: the object to be converted to an object representing JSON
        Returns:
            ``True`` if this converter can convert the given object into
            an object representing JSON,
            ``False`` otherwise.
        """

    @abstractmethod
    def convert(self, o: SourceType_contra, to_json: Callable[[Any], Json]) -> Json:
        """Convert the given object of type ``SourceType_contra`` to an object representing JSON.

        Args:
            o: the object to convert
            to_json: If this converter converts container types like :class:`typing.Sequence`
                this function is used to convert the contained objects into their corresponding
                objects representing JSON.
        Returns:
            the converted object representing JSON.
        Raises:
            ValueError: If the object cannot be converted to an object representing JSON.
        """


class FunctionBasedToSimpleJsonConverter(ToJsonConverter[SourceType_contra]):
    # noinspection GrazieInspection  # pylint: disable=wrong-spelling-in-docstring
    """A function based :class:`ToJsonConverter`.

    Creates a ``ToJsonConverter`` from a function that maps a source type to a simple JSON type.

    Args:
        f: A function that maps a source type into a simple JSON type (int, float, str, bool).
        input_type: None, if the source type can be derived from the function signature
            (using :func:`inspect.signature`) or the concrete source type if this is not
            possible.

    Example FunctionBasedToSimpleJsonConverter:
        >>> from typing import Sequence
        >>> from jsonype import FunctionBasedToSimpleJsonConverter
        >>>
        >>> def abbreviate_str(s: str) -> str:
        ...     return s if len(s) < 8 else f"{s[:2]}...{s[-2:]}"
        >>>
        >>> converter = FunctionBasedToSimpleJsonConverter(abbreviate_str)
        >>> print(converter.convert(
        ...     "Long String",
        ...     lambda a: None
        ... ))
        Lo...ng
        >>> # if the function signature is untyped, the input type can be provided explicitly:
        >>>
        >>> converter2 = FunctionBasedToSimpleJsonConverter(
        ...     lambda s: s if len(s) < 8 else f"{s[:2]}...{s[-2:]}", str)
    """

    def __init__(self,
                 f: Callable[[SourceType_contra], JsonType_co],
                 input_type: type[SourceType_contra] | None = None) -> None:
        self._f = f
        if input_type:
            self._input_type = input_type
            return
        sig = signature(f)
        assert len(sig.parameters) == 1
        input_parameter = next(iter(sig.parameters.values()))
        assert input_parameter.annotation != Parameter.empty
        self._input_type = input_parameter.annotation

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, self._input_type)

    def convert(self, o: SourceType_contra, _to_json: Callable[[Any], Json]) -> Json:
        try:
            return self._f(o)
        except ValueError as e:
            raise ToJsonConversionError(o, str(e)) from e


class FromNone(ToJsonConverter[JsonNull]):
    """Converts a ``None`` instance.

    A ``None`` is converted to ``None``.
    """

    def can_convert(self, o: Any) -> bool:
        return o is None

    def convert(self, o: JsonNull, to_json: Callable[[Any], Json]) -> JsonNull:
        return None


class FromSimple(ToJsonConverter[JsonSimple]):
    """Converts simple objects of type ``int``, ``float``, ``str``, ``bool``.

    The conversion simply returns the given object.
    """

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, get_args(JsonSimple))

    def convert(self, o: JsonSimple, to_json: Callable[[Any], Json]) -> JsonSimple:
        return o


class FromSequence(ToJsonConverter[Sequence[Any]]):
    """Converts objects of type :class:`typing.Sequence`.

    A :class:`typing.Sequence` is converted to a :class:`list` with all elements being converted
    with their respective :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, Sequence)

    def convert(self, o: Sequence[Any], to_json: Callable[[Any], Json]) -> Json:
        return [to_json(e) for e in o]


class FromMapping(ToJsonConverter[Mapping[str, Any]]):
    """Converts objects of type :class:`typing.Mapping`.

    A :class:`typing.Mapping` with ``str`` typed keys is converted to a ``dict`` with all values
    being converted with their respective :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, Mapping)

    def convert(self, o: Mapping[str, Any], to_json: Callable[[Any], Json]) -> Json:
        """Convert the given object of type :class:`typing.Mapping` to an object representing JSON.

        Raises:
            ValueError: If the :class:`typing.Mapping` contains none-``str`` keys.
        """

        def ensure_str(k: Any) -> str:
            if isinstance(k, str):
                return k
            raise ToJsonConversionError(o, f"Contains non str key: {k}")

        return {ensure_str(k): to_json(v) for k, v in o.items()}
