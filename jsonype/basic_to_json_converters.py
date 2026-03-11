from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from inspect import Parameter, isclass, signature
from itertools import cycle
from typing import Any, Generic, Protocol, TypeVar, cast, get_args

from jsonype.base_types import HasRequiredKeys, Json, JsonNull, JsonSimple, ParameterizedTypeInfo

SourceType_contra = TypeVar("SourceType_contra", contravariant=True)
JsonType_co = TypeVar("JsonType_co", bound=JsonSimple, covariant=True)


# pylint: disable=too-few-public-methods
class ContainerElementToJson(Protocol):
    def __call__(self, _element: Any, source_type: type[Any] | None = None) -> Json:
        ...


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
    def can_convert(self, o: Any,
                    source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        """Return if this converter can convert the given object to an object representing JSON.

        Args:
            o: the object to be converted to an object representing JSON
            source_type_info: An optional description of the type of ``o``. If ``None``
                possibly existing type-hints cannot be considered for the conversion. This is
                especially true for :class:`Annotated` type-hints.
        Returns:
            ``True`` if this converter can convert the given object into
            an object representing JSON,
            ``False`` otherwise.
        """

    @abstractmethod
    def convert(self, o: SourceType_contra,
                to_json: ContainerElementToJson,
                source_type_info: ParameterizedTypeInfo[Any] | None = None) -> Json:
        """Convert the given object of type ``SourceType_contra`` to an object representing JSON.

        Args:
            o: the object to convert
            source_type_info: An optional description of the type of ``o``. If ``None``
                possibly existing type-hints cannot be considered for the conversion. This is
                especially true for :class:`Annotated` type-hints.
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
        ...     lambda a, b = None: None
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

    def can_convert(self, o: Any,
                    _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return isinstance(o, self._input_type)

    def convert(self, o: SourceType_contra,
                _to_json: ContainerElementToJson,
                _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> Json:
        try:
            return self._f(o)
        except ValueError as e:
            raise ToJsonConversionError(o, str(e)) from e


class FromNone(ToJsonConverter[JsonNull]):
    """Converts a ``None`` instance.

    A ``None`` is converted to ``None``.
    """

    def can_convert(self, o: Any,
                    _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return o is None

    def convert(self, o: JsonNull,
                to_json: ContainerElementToJson,
                _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> JsonNull:
        return None


class FromSimple(ToJsonConverter[JsonSimple]):
    """Converts simple objects of type ``int``, ``float``, ``str``, ``bool``.

    The conversion simply returns the given object.
    """

    def can_convert(self, o: Any,
                    _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return isinstance(o, get_args(JsonSimple))

    def convert(self, o: JsonSimple,
                to_json: ContainerElementToJson,
                _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> JsonSimple:
        return o


class FromSequence(ToJsonConverter[Sequence[Any]]):
    """Converts objects of type :class:`typing.Sequence`.

    A :class:`typing.Sequence` is converted to a :class:`list` with all elements being converted
    with their respective :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any,
                    _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return isinstance(o, Sequence)

    def convert(self, o: Sequence[Any],
                to_json: ContainerElementToJson,
                source_type_info: ParameterizedTypeInfo[Any] | None = None) -> Json:

        # a Sequence[type] is a Sequence[type | None], but mypy requires this cast
        # Note that in case of tuples there might be multiple generic args, but in case of list
        # there is only one
        generic_args = (
            cast("Sequence[type | None]", source_type_info.generic_args or [None])
            if source_type_info
            else [None])
        return [to_json(e, element_type) for e, element_type in zip(o, cycle(generic_args))]


class FromMapping(ToJsonConverter[Mapping[str, Any]]):
    """Converts objects of type :class:`typing.Mapping`.

    If you also want to use :class:`FromTypedMapping` make sure that this converter is configured
    after the one for :class:`typing.TypedDict` as it will also capture those, but will ignore
    existing type hints.

    A :class:`typing.Mapping` with ``str`` typed keys is converted to a ``dict`` with all values
    being converted with their respective :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any,
                    _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return isinstance(o, Mapping)

    def convert(self, o: Mapping[str, Any],
                to_json: ContainerElementToJson,
                _source_type_info: ParameterizedTypeInfo[Any] | None = None) -> Json:
        """Convert the given object of type :class:`typing.Mapping` to an object representing JSON.

        Raises:
            ValueError: If the :class:`typing.Mapping` contains none-``str`` keys.
        """

        def ensure_str(k: Any) -> str:
            if isinstance(k, str):
                return k
            raise ToJsonConversionError(o, f"Contains non str key: {k}")

        return {ensure_str(k): to_json(v) for k, v in o.items()}


class FromTypedMapping(ToJsonConverter[Mapping[str, Any]]):
    """Converts objects of type :class:`typing.TypedDict`.

    A :class:`typing.TypedDict` is converted to a ``dict`` with all values
    being converted with their respective :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any,
                    source_type_info: ParameterizedTypeInfo[Any] | None = None) -> bool:
        return bool(source_type_info
                    and isclass(source_type_info.full_type)
                    and issubclass(source_type_info.full_type, Mapping)
                    and isinstance(source_type_info.full_type, HasRequiredKeys)
                    and isinstance(o, Mapping))

    def convert(self, o: Mapping[str, Any],
                to_json: ContainerElementToJson,
                source_type_info: ParameterizedTypeInfo[Any] | None = None) -> Json:
        assert source_type_info
        return {k: to_json(v, source_type_info.annotations.get(k)) for k, v in o.items()}
