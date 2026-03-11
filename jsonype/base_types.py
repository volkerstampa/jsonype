from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from inspect import isclass
from itertools import groupby
from typing import (Annotated, Generic, Protocol, TypeAlias, TypeVar, cast, get_args, get_origin,
                    get_type_hints, runtime_checkable)

JsonNull: TypeAlias = None
JsonSimple: TypeAlias = int | float | str | bool
JsonComplex: TypeAlias = Sequence["Json"] | Mapping[str, "Json"]
Json: TypeAlias = JsonNull | JsonSimple | JsonComplex


@dataclass(frozen=True)
class JsonPath:
    """Represent the path to an element in a nested JSON structure.

    The string representation of this path follows the ideas of
    `JSONPath <https://goessner.net/articles/JsonPath/>`_ .
    """

    _elements: tuple[str | int, ...] = ()

    def __str__(self) -> str:
        def key_join(elements: Iterable[str]) -> str:
            return "." + ".".join(elements)

        def index_join(elements: Iterable[int]) -> str:
            return "[" + "][".join(map(str, elements)) + "]"

        path = "".join(key_join(elements) if path_type is str  # type: ignore[arg-type]
                       else index_join(elements)  # type: ignore[arg-type]
                       for path_type, elements in groupby(self._elements, type))
        return f"${path}"

    def append(self, e: str | int) -> "JsonPath":
        return JsonPath((*self._elements, e))


_TargetType = TypeVar("_TargetType")
_SourceType = TypeVar("_SourceType", bound=Json)


@dataclass(frozen=True)
class Options(Generic[_TargetType]):
    from_json: Callable[[Json], _TargetType]
    to_json: Callable[[_TargetType], Json]


def options(
        from_json: Callable[[_SourceType], _TargetType], to_json: Callable[[_TargetType], Json]
) -> Options[_TargetType]:
    # This will fail at runtime. It anyway has to fail at runtime, if the function gets
    # an unexpected type, i.e. the from_json is not compatible to the Annotated type
    # casting here makes the definition on client side easier.
    return Options(cast("Callable[[Json], _TargetType]", from_json), to_json)


def options_from(ty: type | str) -> Options[_TargetType] | None:
    return next((o for o in getattr(ty, "__metadata__", ()) if isinstance(o, Options)), None)


TargetType_co = TypeVar("TargetType_co", covariant=True)


@dataclass(frozen=True)
class ParameterizedTypeInfo(Generic[TargetType_co]):
    """Information about a parameterized type.

    Args:
        full_type: full type information, for example ``Mapping[str, int]``.
            A possibly existing ``Annotated`` is removed, so ``Annotated[int, ...]`` becomes
            ``int``.
        origin_of_generic: the unsubscripted version of ``full_type``
            (i.e. without its type parameters), for example ``Mapping``.
            ``None`` if ``full_type`` is not a generic type.
            Can be computed with :func:`typing.get_origin`.
        annotations: a mapping from member name to its type. Can be computed with
            :func:``typing.get_annotations``.
        generic_args: just the arguments of the generic type as a tuple, for example ``(str, int)``.
            ``()`` if ``full_type`` is not a generic type.
            Can be computed with :func:`typing.get_args`.
        opts: First Options instance found in metadata if ``full_type`` was ``Annotated``.
    """

    full_type: type[TargetType_co]
    origin_of_generic: type | None
    annotations: Mapping[str, type]
    generic_args: Sequence[type]
    opts: Options[TargetType_co] | None

    @classmethod
    def from_optionally_generic(
            cls, t: type[TargetType_co]
    ) -> "ParameterizedTypeInfo[TargetType_co]":
        origin = get_origin(t)
        # mypy is fine with this
        # noinspection PyTypeChecker
        return cls(
            unnotate(t, origin),
            origin,
            get_type_hints(t, include_extras=True) if isclass(t) else {},
            get_args(t),
            options_from(t),
        )


def unnotate(ty: type[TargetType_co], origin: type | None) -> type[TargetType_co]:
    # Annotated is a Callable and yes we want to compare against it
    return (getattr(ty, "__origin__", ty) if origin is Annotated  # type: ignore[comparison-overlap]
            else ty)


@runtime_checkable
class HasRequiredKeys(Protocol):  # pylint: disable=too-few-public-methods
    __required_keys__: frozenset[str]
