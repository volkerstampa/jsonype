from inspect import get_annotations
from random import choice, choices, gauss, randint, randrange, uniform
from string import ascii_letters, digits, printable
from sys import float_info
from types import NoneType
from typing import (Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple, TypeAlias,
                    TypedDict, TypeVar, Union, cast)

from pytest import mark, raises

from jsonype import FromJsonConversionError, TypedJson

_T = TypeVar("_T")


ObjectFactory: TypeAlias = Callable[[int, Sequence["ObjectFactory[_T]"]], tuple[_T, type[_T]]]

typed_json = TypedJson()
strict_typed_json = TypedJson(strict=True)


@mark.parametrize(
    "simple_obj",
    [0, -1, 2, 0.0, 1.0, -2.0, True, False, "Hello", "", None],
)
def test_simple(simple_obj: Any) -> None:
    assert_can_convert_from_to_json(simple_obj, type(simple_obj))


@mark.parametrize("simple_obj", [0, "Hello", None])
def test_simple_with_union_type(simple_obj: Union[int, str, None]) -> None:
    # Union is a type-special-form so cast to type explicitly
    assert_can_convert_from_to_json(
        simple_obj, cast(type[Optional[Union[int, str]]], Optional[Union[int, str]]))


@mark.parametrize(
    ("li", "ty"),
    [
        ([0, -1, 2], int),
        ([0.0, 1.0, -2.0], float),
        ([True, False], bool),
        (["Hello", ""], str),
        ([None], NoneType),
    ],
)
def test_homogeneous_list(li: Sequence[Any], ty: TypeAlias) -> None:
    assert_can_convert_from_to_json(li, list[ty])


@mark.parametrize("li", [[1], ["Hi"]])
def test_untyped_list(li: Sequence[Any]) -> None:
    assert_can_convert_from_to_json(li, list)


def test_inhomogeneous_list() -> None:
    assert_can_convert_from_to_json([1, 0., True, None, "Hello"],
                                    list[Union[int, float, bool, None, str]])


def test_inhomogeneous_tuple() -> None:
    assert_can_convert_from_to_json((1, 0., True, None, "Hello"),
                                    tuple[int, float, bool, None, str])


def test_empty_tuple() -> None:
    assert_can_convert_from_to_json((), tuple[()])


@mark.parametrize(
    ("m", "ty"),
    [({"k1": 1}, int), ({"k1": True, "k2": False}, bool), ({"k1": None}, NoneType)],
)
def test_homogeneous_mapping(m: Mapping[str, Any], ty: TypeAlias) -> None:
    assert_can_convert_from_to_json(m, dict[str, ty])


def test_inhomogeneous_mapping() -> None:
    assert_can_convert_from_to_json({"k1": 1, "k2": "Demo"}, dict[str, Union[int, str]])


def test_typed_dict_relaxed() -> None:
    class Map(TypedDict):
        k1: float
        k2: int

    inp = {"k1": 1., "k2": 2, "un": "used"}
    expected = {k: v for k, v in inp.items() if k in get_annotations(Map)}
    assert_can_convert_from_to_json_relaxed(inp, expected, Map)


def test_typed_dict() -> None:
    class Map(TypedDict):
        k1: float
        k2: int

    assert_can_convert_from_to_json({"k1": 1., "k2": 2}, Map)


def test_typed_dict_fail_if_key_missing() -> None:
    class Map(TypedDict):
        k1: float
        k2: int

    with raises(FromJsonConversionError) as exc_info:
        typed_json.from_json({"k1": 1.}, Map)
    assert "k2" in str(exc_info.value)


def test_random_objects() -> None:
    for _ in range(500):
        assert_can_convert_from_to_json(*(_random_typed_object(8)))


def assert_can_convert_from_to_json(obj: Any, ty: type[_T]) -> None:
    try:
        assert obj == strict_typed_json.from_json(typed_json.to_json(obj), ty)
    except AssertionError:
        print(f"Cannot convert {obj} to {ty}")  # noqa: T201
        raise


def assert_can_convert_from_to_json_relaxed(inp: Any, expected: Any, ty: type[_T]) \
        -> None:
    try:
        assert expected == typed_json.from_json(typed_json.to_json(inp), ty)
    except AssertionError:
        print(f"Cannot convert {inp} to {ty}")  # noqa: T201
        raise


def _random_typed_object(size: int,
                         factories: Optional[Sequence[ObjectFactory[_T]]] = None) \
        -> tuple[_T, type[_T]]:
    factories = factories or _all_types_factories()
    return choice(factories)(size, factories)


def _ambiguous_types_factories() -> Sequence[ObjectFactory[Any]]:
    return (_random_tuple,
            _random_tuple_with_ellipsis,
            _random_untyped_list,
            _random_untyped_map)


def _unambiguous_types_factories() -> Sequence[ObjectFactory[Any]]:
    return (_random_int,
            _random_float,
            _random_bool,
            _none,
            _random_str,
            _random_sequence,
            _random_map,
            _random_typed_map)


def _all_types_factories() -> Sequence[ObjectFactory[Any]]:
    return tuple(_ambiguous_types_factories()) + tuple(_unambiguous_types_factories())


def _random_int(_size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[int, type[int]]:
    return randint(-2 ** 63, 2 ** 63 - 1), int


def _random_float(_size: int, _factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[float, type[float]]:
    f = choices([-float_info.max,
                uniform(-float_info.max, 0),
                gauss(0, 10),
                uniform(0, float_info.max),
                float_info.max],
                weights=[1, 3, 5, 3, 1])
    return f[0], float


def _random_bool(_size: int, _factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[bool, type[bool]]:
    return bool(randint(0, 1)), bool


def _none(_size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[None, Any]:
    return None, Any


def _random_str(size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[str, type[str]]:
    return "".join(choices(printable, k=randrange(size))), str


def _random_sequence(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[Sequence[_T]]]:
    seq, types = _random_values(size, factories)
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    element_type: TypeAlias = cast(type, Union[*types] if seq else Any)
    return list(seq), Sequence[element_type]


def _random_untyped_list(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[list[Any]]]:
    unambiguous_factories = tuple(
        frozenset(_unambiguous_types_factories()).intersection(frozenset(factories)))
    seq, _types = _random_values(size, unambiguous_factories)
    return list(seq), List


def _random_tuple(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
    seq, types = _random_values(size, factories)
    # tuple[*var] it interpreted as object, so it needs a cast
    return tuple(seq), cast(type[tuple[_T, ...]], Tuple[*types])


def _random_tuple_with_ellipsis(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
    unambiguous_factories = tuple(
        frozenset(_unambiguous_types_factories()).intersection(frozenset(factories)))
    seq, types = _random_values(size, unambiguous_factories)
    # tuple[*var] it interpreted as object, so it needs a cast
    return tuple(seq), cast(type[tuple[_T, ...]],
                            Tuple[*insert_random_ellipsis(types)])


def _random_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
    vals, types = _random_values(size, factories)
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    value_types: TypeAlias = cast(type, Union[*types] if vals else Any)
    return ({_random_str(size, factories)[0]: val for val in vals},
            Mapping[str, value_types])


def _random_untyped_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, Any]]]:
    unambiguous_factories = tuple(
        frozenset(_unambiguous_types_factories()).intersection(frozenset(factories)))
    vals, _types = _random_values(size, unambiguous_factories)
    return {_random_str(size, factories)[0]: val for val in vals}, Mapping


def _random_typed_map(size: int, factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[Mapping[str, Any], type[Mapping[str, Any]]]:
    vals, types = _random_values(size, factories)
    keys = [_random_symbol() for _ in vals]
    # https://github.com/python/mypy/issues/7178
    map_type = TypedDict(_random_symbol(), dict(zip(keys, types)))  # type: ignore[misc] # noqa: UP013
    # the types of vals are in types, and they are zipped in the same way with
    # the keys as the vals are zipped here so this should actually be safe.
    return map_type(**dict(zip(keys, vals))), map_type  # type: ignore[typeddict-item]


def _random_symbol() -> str:
    return "".join(choices(ascii_letters + digits, k=10))


def _random_values(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], Sequence[type[_T]]]:
    previous_types: list[type[_T]] = []

    def add_to_previous(val: Any, ty: type[_T]) -> tuple[_T, type[_T]]:
        previous_types.append(ty)
        return val, ty

    def cannot_convert(val: _T, ty: type[_T]) -> bool:
        try:
            typed_json.from_json(typed_json.to_json(val), ty)
        except ValueError:
            return True
        return False

    def cannot_convert_to_previous_type(val: _T) -> bool:
        return all(cannot_convert(val, ty) for ty in previous_types)

    values_with_types: Iterable[tuple[_T, type[_T]]] = \
        (_random_typed_object(size // 2, factories) for _ in range(randrange(size)))
    # zip is an Iterable which has only a single type-parameter (i.e. must be homogeneous)
    # but when some (Any, type) tuples are zipped we do get a ([Any], [type])
    value_and_types = cast(
        tuple[Sequence[_T], Sequence[type[_T]]],
        tuple(zip(*(add_to_previous(val, ty) for val, ty in values_with_types if
              cannot_convert_to_previous_type(val)))))
    return value_and_types or ((), ())


def insert_random_ellipsis(types: Sequence[type]) -> Sequence[type]:
    if not types:
        return ()
    ellipsis_start = randint(0, len(types) - 1)
    ellipsis_end = randint(ellipsis_start + 1, len(types))
    types_with_ellipsis: list[Any] = list(types)
    types_with_ellipsis[ellipsis_start:ellipsis_end] = [...]
    return types_with_ellipsis
