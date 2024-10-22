from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, make_dataclass
from functools import partial
from inspect import get_annotations, isclass
from json import dumps, loads
from random import choice, choices, gauss, randint, randrange, uniform
from string import ascii_letters, digits, printable
from sys import float_info
from types import NoneType
from typing import (Any, Callable, NamedTuple, Optional, TypeAlias, TypedDict, TypeVar, Union, cast,
                    get_args, get_origin)

from _pytest.main import Failed
from pytest import fail, mark, raises

from jsonype import FromJsonConversionError, Json, JsonPath, TypedJson
from jsonype.dataclass_converters import DataclassTarget_co
from jsonype.named_tuple_converters import NamedTupleTarget_co

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


def test_str_with_int() -> None:
    with raises(FromJsonConversionError):
        typed_json.from_json(42, str)


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


def test_named_tuple() -> None:
    class SubDemo(NamedTuple):
        field: str

    class Demo(NamedTuple):
        sub: SubDemo

    assert_can_convert_from_to_json(Demo(SubDemo("Hello")), Demo)


def test_dataclass() -> None:
    @dataclass
    class SubDemo:
        field: str

    @dataclass
    class Demo:
        sub: SubDemo

    assert_can_convert_from_to_json(Demo(SubDemo("Hello")), Demo)


def test_error_contains_path_at_root() -> None:
    with raises(FromJsonConversionError) as e:
        typed_json.from_json(1, str)
    assert e.value.path == JsonPath()


def test_error_contains_path_in_array() -> None:
    with raises(FromJsonConversionError) as e:
        typed_json.from_json([1], list[str])
    assert e.value.path == JsonPath((0,))


def test_random_objects() -> None:
    for _ in range(500):
        assert_can_convert_from_to_json(*(_random_typed_object(8)))


def test_random_objects_with_failure() -> None:
    for _ in range(500):
        ty, erroneous_json, error = _random_typed_object_with_failure(8)
        unexpected_result = None
        try:
            with raises(FromJsonConversionError) as e:
                # mypy is fine with this
                # noinspection PyTypeChecker
                unexpected_result = typed_json.from_json(erroneous_json, ty)
            assert_from_json_conversion_error_equals(error, e.value)
        except (AssertionError, Failed):
            # helps when debugging test failures
            print(f"Unexpected or no FromJsonConversionError when converting "  # noqa: T201
                  f"{erroneous_json} to {ty}"
                  + (f" result: {unexpected_result}" if unexpected_result is not None else ""))
            raise


def assert_from_json_conversion_error_equals(
        a: FromJsonConversionError, b: FromJsonConversionError
) -> None:
    # combining test-assertion actually improve the error message as pytest
    # analyses the entire expression
    assert a.args[1:3] == b.args[1:3] and a.path == b.path  # noqa: PT018


def assert_can_convert_from_to_json(obj: Any, ty: type[_T]) -> None:
    try:
        js = typed_json.to_json(obj)
        js = loads(dumps(js))
        assert strict_typed_json.from_json(js, ty) == obj
    except AssertionError:
        # helps when debugging test failures
        print(f"Cannot convert {obj} to {ty}")  # noqa: T201
        raise


def assert_can_convert_from_to_json_relaxed(inp: Any, expected: Any, ty: type[_T]) \
        -> None:
    try:
        assert expected == typed_json.from_json(typed_json.to_json(inp), ty)
    except AssertionError:
        # helps when debugging test failures
        print(f"Cannot convert {inp} to {ty}")  # noqa: T201
        raise


def _random_typed_object_with_failure(size: int) -> tuple[type, Json, FromJsonConversionError]:
    random_tuple_with_ellipsis_not_at_first_pos = cast(
        ObjectFactory[tuple[Any]],
        partial(
            _random_tuple_with_ellipsis,
            insert_random_ellipsis=partial(_insert_random_ellipsis,
                                           allow_ellipsis_at_first_pos=False)
        )
    )
    factories: tuple[ObjectFactory[Any], ...] = tuple(
        {*_all_types_factories(),
         _random_homogeneous_map,
         _random_homogeneous_sequence,
         random_tuple_with_ellipsis_not_at_first_pos}
        # _none has Any as type, and you cannot create and error for the Any type
        # _random_sequence and _map have Union types as values, and it seems to be
        # too much effort to randomly generate an erroneous value for a Union type.
        # To prevent that in case of a tuple a value is replaced that corresponds to ellipsis (...)
        # 1. generate ellipsis only after the first element and 2. replace always the first element
        - {_none, _random_sequence, _random_map, _random_tuple_with_ellipsis}
    )
    obj, ty = cast(tuple[object, type], _random_typed_object(size, factories))
    js = typed_json.to_json(obj)
    js, error = _json_with_error(js, JsonPath(), ty)
    return ty, js, error


# Should be easy enough to read despite the many returns
# return early if condition on type is met.
def _json_with_error(  # noqa: R901, PLR0911
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    origin = get_origin(ty)
    if ty is str:
        return _str_with_error(path, ty)
    if ty in {None, int, float, bool}:
        return _non_str_primitive_with_error(path, ty)
    if origin is None:
        return _untyped_collection_with_error(path, ty)
    if isclass(origin) and issubclass(origin, tuple):
        return _tuple_with_error(js, path, ty)
    if isclass(origin) and issubclass(origin, Sequence):
        return _sequence_with_error(js, path, ty)
    if isclass(ty) and issubclass(ty, Mapping):
        return _typed_mapping_with_error(js, path, ty)
    if isclass(origin) and issubclass(origin, Mapping):
        return _mapping_with_error(js, path, ty)
    if origin is Union:
        assert len(get_args(ty)) == 1, str(get_args(ty))
        return _mapping_with_error(js, path, get_args(ty)[0])
    fail(f"Unexpected type: {ty} (origin: {origin})")


def _non_str_primitive_with_error(path: JsonPath, ty: type) -> tuple[str, FromJsonConversionError]:
    erroneous_js = "42"
    return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)


def _str_with_error(path: JsonPath, ty: type) -> tuple[str | int, FromJsonConversionError]:
    erroneous_js: str | int = 42
    return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)


def _untyped_collection_with_error(
        path: JsonPath, ty: type
) -> tuple[str | int, FromJsonConversionError]:
    erroneous_js: str | int = 42
    return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)


def _sequence_with_error(
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    assert isinstance(js, Sequence)
    if not js or not get_args(ty):
        erroneous_js = 42
        return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)
    contained_type = get_args(ty)[0]
    random_index = randrange(len(js))
    erroneous_element, error = _json_with_error(
        js[random_index], path.append(random_index), contained_type)
    erroneous_list = list(js)
    erroneous_list[random_index] = erroneous_element
    return erroneous_list, error


def _tuple_with_error(
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    assert isinstance(js, Sequence)
    contained_types = get_args(ty)
    if not js:
        erroneous_js = 42
        return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)
    if choice([True, False]) or ... in contained_types:
        # prevents to pick element with "type" ...
        index = 0
        erroneous_element, error = _json_with_error(
            js[index], path.append(index), contained_types[index])
        return tuple(erroneous_element if i == index else e for i, e in enumerate(js)), error
    erroneous_json = (*tuple(js), 1)
    return erroneous_json, FromJsonConversionError(erroneous_json, path, ty)


def _mapping_with_error(
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    assert isinstance(js, Mapping)
    if not js or not get_args(ty):
        erroneous_js = 42
        return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)
    value_type = get_args(ty)[1]
    random_index = randrange(len(js))
    key, value = list(js.items())[random_index]
    erroneous_value, error = _json_with_error(value, path.append(key), value_type)
    return {**js, key: erroneous_value}, error


def _typed_mapping_with_error(
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    assert isinstance(js, Mapping)
    annotations = get_annotations(ty)
    if not js:
        erroneous_js = 42
        return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)
    random_key = choice(list(annotations.keys()))
    value = js[random_key]
    erroneous_value, error = _json_with_error(
        value, path.append(random_key), annotations[random_key]
    )
    return {**js, random_key: erroneous_value}, error


def _random_typed_object(size: int,
                         factories: Optional[Sequence[ObjectFactory[_T]]] = None) \
        -> tuple[_T, type[_T]]:
    factories = factories or _all_types_factories()
    return choice(factories)(size, factories)


def _ambiguous_types_factories() -> Sequence[ObjectFactory[Any]]:
    return (_random_tuple,
            _random_tuple_with_ellipsis,
            _random_untyped_list,
            _random_untyped_map,
            _random_named_tuple,
            _random_dataclass)


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


def _random_homogeneous_sequence(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[Sequence[_T]]]:
    seq, types = _random_values(size, factories)
    # Union[types[0]] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    element_type: TypeAlias = cast(type, Union[types[0]] if seq else Any)
    return [e for e, ty in zip(seq, types) if ty == types[0]], Sequence[element_type]


def _random_untyped_list(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[list[Any]]]:
    unambiguous_factories = tuple(
        frozenset(_unambiguous_types_factories()).intersection(frozenset(factories)))
    seq, _types = _random_values(size, unambiguous_factories)
    return list(seq), list


def _random_tuple(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
    seq, types = _random_values(size, factories)
    # tuple[*var] it interpreted as object, so it needs a cast
    return tuple(seq), cast(type[tuple[_T, ...]], tuple[*types])  # type: ignore[valid-type]


def _insert_random_ellipsis(types: Sequence[type], allow_ellipsis_at_first_pos: bool = True) \
        -> Sequence[type]:
    first_allowed_pos = 0 if allow_ellipsis_at_first_pos else 1
    if len(types) <= first_allowed_pos:
        return types
    ellipsis_start = randint(first_allowed_pos, len(types) - 1)
    ellipsis_end = randint(ellipsis_start + 1, len(types))
    types_with_ellipsis: list[Any] = list(types)
    types_with_ellipsis[ellipsis_start:ellipsis_end] = [...]
    return types_with_ellipsis


def _random_tuple_with_ellipsis(
        size: int,
        factories: Sequence[ObjectFactory[_T]],
        insert_random_ellipsis: Callable[[Sequence[type]], Sequence[type]] = _insert_random_ellipsis
) -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
    unambiguous_factories = tuple(
        frozenset(_unambiguous_types_factories()).intersection(frozenset(factories)))
    seq, types = _random_values(size, unambiguous_factories)
    # tuple[*var] it interpreted as object, so it needs a cast
    return tuple(seq), cast(type[tuple[_T, ...]],
                            tuple[*insert_random_ellipsis(types)])  # type: ignore[misc]


def _random_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
    vals, types = _random_values(size, factories)
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise value_types is not a valid type
    # noinspection PyTypeHints
    value_types: TypeAlias = cast(type, Union[*types] if vals else Any)
    return ({_random_str(size, factories)[0]: val for val in vals},
            Mapping[str, value_types])


def _random_homogeneous_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
    vals, types = _random_values(size, factories)
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    value_type: TypeAlias = cast(type, Union[types[0]] if vals else Any)
    return ({_random_str(size, factories)[0]: val
             for val, ty in zip(vals, types) if ty == types[0]},
            Mapping[str, value_type])


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


def _random_named_tuple(size: int, factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[NamedTupleTarget_co, type[NamedTupleTarget_co]]:
    vals, types = _random_values(size, factories)
    keys = [_random_symbol() for _ in vals]
    # Functional syntax to construct NamedTuple classes -> _make exists
    namedtuple_type = \
        cast(type[NamedTupleTarget_co], NamedTuple(_random_symbol(), list(zip(keys, types))))
    # _make is actually public
    # noinspection PyProtectedMember
    return namedtuple_type._make(vals), namedtuple_type  # noqa: E1101


def _random_dataclass(size: int, factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[DataclassTarget_co, type[DataclassTarget_co]]:
    vals, types = _random_values(size, factories)
    keys = [_random_symbol() for _ in vals]
    dataclass_type = make_dataclass(_random_symbol(), list(zip(keys, types)))
    # dataclass_type is a dataclass-type as it was created with make_dataclass
    # noinspection PyTypeChecker
    return dataclass_type(**dict(zip(keys, vals))), dataclass_type


def _random_symbol() -> str:
    return "".join([choice(ascii_letters), *choices(ascii_letters + digits, k=10)])


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
