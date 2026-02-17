from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, make_dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from functools import partial
from inspect import get_annotations, isclass
from json import dumps, loads
from pathlib import Path
from random import choice, choices, gauss, randint, randrange, uniform
from string import ascii_letters, digits, printable
from sys import float_info
from types import NoneType
from typing import (Annotated, Any, Literal, NamedTuple, TypeAlias, TypedDict, TypeVar, Union, cast,
                    get_args, get_origin)
from urllib.parse import SplitResult, urlsplit
from uuid import UUID, uuid4

from _pytest.main import Failed
from pytest import fail, mark, raises

from jsonype import (FromJsonConversionError, FromJsonConverter, Json, JsonPath,
                     ParameterizedTypeInfo, ToJsonConversionError, ToJsonConverter, TypedJson,
                     UnsupportedSourceTypeError, opts)
from jsonype.basic_to_json_converters import SourceType_contra
from jsonype.dataclass_converters import DataclassTarget_co
from jsonype.named_tuple_converters import NamedTupleTarget_co

_T = TypeVar("_T")


ObjectFactory: TypeAlias = Callable[[int, Sequence["ObjectFactory[_T]"]], tuple[_T, type[_T]]]

typed_json = TypedJson.default()
strict_typed_json = TypedJson.default(strict=True)


@mark.parametrize(
    "simple_obj",
    [0, -1, 2, 0.0, 1.0, -2.0, True, False, "Hello", "", None],
)
def test_simple(simple_obj: Any) -> None:
    assert_can_convert_from_to_json(simple_obj, type(simple_obj))


@mark.parametrize(
    ("simple_obj", "ty"),
    [(datetime.now(UTC), datetime),
     (datetime.now(UTC).date(), date),
     (datetime.now(UTC).time(), time),
     (uuid4(), UUID),
     (Path.cwd(), Path),
     (urlsplit("scheme://netloc/path?query#fragment"), SplitResult),
     (bytes([0, 1, 2]), bytes)],
)
def test_simple_conversions(simple_obj: Any, ty: type[_T]) -> None:
    assert_can_convert_from_to_json(simple_obj, ty)


@mark.parametrize("simple_obj", [0, "Hello", None])
def test_simple_with_union_type(simple_obj: int | str | None) -> None:
    # Union is a type-special-form so cast to type explicitly
    assert_can_convert_from_to_json(
        simple_obj, cast("type[Union[int, str, None]]", Union[int, str, None]))  # noqa: UP007


@mark.parametrize("simple_obj", [0, "Hello", None])
def test_simple_with_union_type_new_syntax(simple_obj: int | str | None) -> None:
    assert_can_convert_from_to_json(
        simple_obj, cast("type[int | str | None]", int | str | None))


def test_str_with_int() -> None:
    with raises(FromJsonConversionError):
        typed_json.from_json(42, str)


@mark.parametrize(
    ("literal", "ty"),
    [(2, Literal[2]), (True, Literal[True]), ("Hello", Literal["Hello"])],
)
def test_literal(literal: int | bool | str, ty: type[_T]) -> None:
    assert_can_convert_from_to_json(literal, ty)


def test_type_with_no_converter() -> None:
    class UnsupportedType:  # pylint: disable=too-few-public-methods
        pass

    with raises(UnsupportedSourceTypeError):
        assert_can_convert_from_to_json(UnsupportedType(), UnsupportedType)


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
                                    list[int | float | bool | None | str])


def test_inhomogeneous_tuple() -> None:
    assert_can_convert_from_to_json((1, 0., True, None, "Hello"),
                                    tuple[int, float, bool, None, str])


def test_empty_tuple() -> None:
    assert_can_convert_from_to_json((), tuple[()])


def test_tuple_with_multiple_ellipsis() -> None:
    with raises(FromJsonConversionError) as e:
        # disable type-check to test edge case
        typed_json.from_json([1], tuple[int, ..., ...])  # type: ignore[misc]

    assert "No suitable converter registered" in str(e.value)


@mark.parametrize(
    ("m", "ty"),
    [({"k1": 1}, int), ({"k1": True, "k2": False}, bool), ({"k1": None}, NoneType)],
)
def test_homogeneous_mapping(m: Mapping[str, Any], ty: TypeAlias) -> None:
    assert_can_convert_from_to_json(m, dict[str, ty])


def test_inhomogeneous_mapping() -> None:
    assert_can_convert_from_to_json({"k1": 1, "k2": "Demo"}, dict[str, int | str])


def test_mapping_with_non_str_key_type() -> None:
    with raises(FromJsonConversionError) as e:
        typed_json.from_json({"k1": 1}, dict[int, int])

    assert "No suitable converter registered" in str(e.value)


def test_mapping_with_non_str_key() -> None:
    non_str_key = 123
    with raises(ToJsonConversionError) as e:
        typed_json.to_json({non_str_key: 42})

    assert str(non_str_key) in str(e.value)


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


def test_typed_dict_strict_fail_if_extra_key() -> None:
    class Map(TypedDict):
        k1: float
        k2: int

    with raises(FromJsonConversionError) as exc_info:
        strict_typed_json.from_json({"k1": 1., "k2": 2, "extra": 3}, Map)
    assert "extra" in str(exc_info.value)


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


def test_with_prepended_custom_from_converter() -> None:
    tj = typed_json.prepend([_StringToFloat()], [])

    float_list: Sequence[str | float] = ["1.0", 2.0]
    result = tj.from_json(float_list, list[float | str])

    # StringToFloat has precedence over str to str
    assert result == [float(s) for s in float_list]


def test_with_prepended_custom_to_converter() -> None:
    tj = typed_json.prepend([], [_FloatToString()])

    float_list = [1.0, "2.0"]
    result = tj.to_json(float_list)

    # FloatToStr has precedence over float to float
    assert result == [str(f) for f in float_list]


def test_with_appended_custom_from_converter_where_other_converter_exists() -> None:
    tj = typed_json.append([_StringToFloat()], [])

    float_list: Sequence[str | float] = ["1.0", 2.0]
    result = tj.from_json(float_list, list[float | str])

    assert result == float_list


def test_with_appended_custom_to_converter_where_other_converter_exists() -> None:
    tj = typed_json.append([], [_FloatToString()])

    float_list = [1.0, "2.0"]
    result = tj.to_json(float_list)

    assert result == float_list


def test_with_appended_from_converter_for_custom_type() -> None:
    # enough for testing
    class MyType:  # pylint: disable=too-few-public-methods
        pass

    class StringToMyType(FromJsonConverter[MyType, None]):

        def can_convert(self, js: Json, target_type_info: ParameterizedTypeInfo[Any]) -> bool:
            return js == MyType.__name__ and target_type_info.full_type is MyType

        def convert(self, js: Json, target_type_info: ParameterizedTypeInfo[MyType],
                    path: JsonPath,
                    from_json: Callable[[Json, type[None], JsonPath],
                    None]) -> MyType:
            return MyType()

    tj = typed_json.append([StringToMyType()], [])
    assert isinstance(tj.from_json(MyType.__name__, MyType), MyType)


def test_with_appended_to_converter_for_custom_type() -> None:
    # enough for testing
    class MyType:  # pylint: disable=too-few-public-methods
        pass

    class MyTypeToString(ToJsonConverter[MyType]):
        def can_convert(self, o: Any) -> bool:
            return isinstance(o, MyType)

        def convert(self, o: SourceType_contra, to_json: Callable[[Any], Json]) -> Json:
            return MyType.__name__

    tj = typed_json.append([], [MyTypeToString()])
    assert tj.to_json(MyType()) == MyType.__name__


def test_annotated_with_custom_serializer() -> None:
    @dataclass
    class Data:
        number: Annotated[int, opts(from_json=int, to_json=str)]

    expected = Data(5)
    js = typed_json.to_json(expected)
    actual = typed_json.from_json(js, Data)

    assert actual == expected
    assert js == {"number": str(expected.number)}


def test_with_no_suitable_from_converter() -> None:
    with raises(FromJsonConversionError) as e:
        TypedJson([], []).from_json(42, int)
    assert "No suitable converter registered" in str(e.value)


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
        unexpected_result: Any = None
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
        expected: FromJsonConversionError, actual: FromJsonConversionError
) -> None:
    # combining test-assertion actually improve the error message as pytest
    # analyses the entire expression
    assert expected.args[1:3] == actual.args[1:3] and expected.path == actual.path  # noqa: PT018


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
    # See comment below on removal of _random_tuple_with_ellipsis why this is required
    random_tuple_with_ellipsis_not_at_first_pos = cast(
        "ObjectFactory[tuple[Any]]",
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
    obj, ty = cast("tuple[object, type]", _random_typed_object(size, factories))
    js = typed_json.to_json(obj)
    js, error = _json_with_error(js, JsonPath(), ty)
    return ty, js, error


# Should be easy enough to read despite the many returns
# return early if condition on type is met.
# correct according to mypy
# noinspection PyTypeChecker
# pylint: disable-next=too-many-return-statements,inconsistent-return-statements
def _json_with_error(  # noqa: R901, PLR0911, C901
        js: Json, path: JsonPath, ty: type
) -> tuple[Json, FromJsonConversionError]:
    origin = get_origin(ty)
    if ty is str:
        return _str_with_error(path, ty)
    if ty in {None, int}:
        return _non_str_simple_with_error(path, ty)
    if origin is None:
        return _unparameterized_with_error(path, ty)
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


def _non_str_simple_with_error(path: JsonPath, ty: type) -> tuple[str, FromJsonConversionError]:
    erroneous_js = "42"
    return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)


def _str_with_error(path: JsonPath, ty: type) -> tuple[str | int, FromJsonConversionError]:
    erroneous_js: str | int = 42
    return erroneous_js, FromJsonConversionError(erroneous_js, path, ty)


def _unparameterized_with_error(
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
                         factories: Sequence[ObjectFactory[_T]] | None = None) \
        -> tuple[_T, type[_T]]:
    factories = factories or _all_types_factories()
    return choice(factories)(size, factories)


def _ambiguous_types_factories() -> Sequence[ObjectFactory[Any]]:
    return (_random_tuple,
            _random_tuple_with_ellipsis,
            _random_untyped_list,
            _random_untyped_map,
            # a str-datetime is not converted to datetime if contained in an untyped collection
            _random_datetime,
            _random_date,
            _random_time,
            _random_uuid,
            _random_path,
            _random_bytes,
            _random_url,
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


def _random_datetime(
        _size: int, _factories: Sequence[ObjectFactory[Any]]
) -> tuple[datetime, type[datetime]]:
    min_datetime = datetime.min.replace(tzinfo=UTC)
    max_datetime = datetime.max.replace(tzinfo=UTC)
    # conversion to from float with (from)timestamp() is not precise due to rounding errors
    # so shift max by 1ms to prevent ValueErrors
    max_datetime_adjusted = datetime.max.replace(tzinfo=timezone(timedelta(milliseconds=1)))
    result = choices([min_datetime,
                      uniform(min_datetime.timestamp(), max_datetime_adjusted.timestamp()),
                      max_datetime],
                     weights=[1, 5, 1])[0]
    if isinstance(result, float):
        result = datetime.fromtimestamp(result, tz=UTC)
    assert isinstance(result, datetime)
    return result, datetime


def _random_date(
        _size: int, _factories: Sequence[ObjectFactory[Any]]
) -> tuple[date, type[date]]:
    result = choices([date.min.toordinal(),
                      randint(date.min.toordinal(), date.max.toordinal()),
                      date.max.toordinal()],
                     weights=[1, 5, 1])[0]
    return date.fromordinal(result), date


def _random_time(
        _size: int, _factories: Sequence[ObjectFactory[Any]]
) -> tuple[time, type[time]]:
    result = choices([time.min,
                      time(hour=randrange(24),
                           minute=randrange(60),
                           second=randrange(60),
                           microsecond=randrange(1000000)),
                      time.max],
                     weights=[1, 5, 1])[0]
    return result, time


def _random_uuid(_size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[UUID, type[UUID]]:
    return uuid4(), UUID


def _random_path(size: int, factories: Sequence[ObjectFactory[Any]]) -> tuple[Path, type[Path]]:
    segments = (_random_str(size, factories)[0] for _ in range(randint(1, size)))
    return Path().joinpath(*segments), Path


def _random_bytes(size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[bytes, type[bytes]]:
    return bytes(randint(0, 255) for _ in range(randint(1, size))), bytes


def _random_url(size: int,
                _factories: Sequence[ObjectFactory[Any]]) -> tuple[SplitResult, type[SplitResult]]:
    def random_ascii_str() -> str:
        return "".join(choices(ascii_letters, k=randrange(size)))

    # inspection is wrong
    # noinspection PyArgumentList
    return SplitResult(scheme=random_ascii_str().lower(),
                       netloc=random_ascii_str(),
                       path=f"/{random_ascii_str()}",
                       query=random_ascii_str(),
                       fragment=random_ascii_str()), SplitResult


def _random_sequence(size: int, _factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[Sequence[_T]]]:
    seq, types = _random_values(size, _unambiguous_types_factories())
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    element_type: TypeAlias = cast("type", Union[*types] if seq else Any)
    return list(seq), Sequence[element_type]


def _random_homogeneous_sequence(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Sequence[_T], type[Sequence[_T]]]:
    seq, types = _random_values(size, factories)
    # Union[types[0]] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    element_type: TypeAlias = cast("type", types[0] if seq else Any)
    return [e for e, ty in zip(seq, types, strict=False) if ty == types[0]], Sequence[element_type]


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
    return tuple(seq), cast("type[tuple[_T, ...]]", tuple[*types])  # type: ignore[valid-type]


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
    return tuple(seq), cast("type[tuple[_T, ...]]",
                            tuple[*insert_random_ellipsis(types)])  # type: ignore[misc]


def _random_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
    vals, types = _random_values(size, _unambiguous_types_factories())
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise value_types is not a valid type
    # noinspection PyTypeHints
    value_types: TypeAlias = cast("type", Union[*types] if vals else Any)
    return ({_random_str(size, factories)[0]: val for val in vals},
            Mapping[str, value_types])


def _random_homogeneous_map(size: int, factories: Sequence[ObjectFactory[_T]]) \
        -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
    vals, types = _random_values(size, factories)
    # Union[*types] is not a valid type so cast to a type
    # TypeAliases shall be top-level, but otherwise element_type is not a valid type
    # noinspection PyTypeHints
    value_type: TypeAlias = cast("type", types[0] if vals else Any)
    return ({_random_str(size, factories)[0]: val
             for val, ty in zip(vals, types, strict=False) if ty == types[0]},
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
    map_type = TypedDict(_random_symbol(),  # type: ignore[misc] # noqa: UP013
                         dict(zip(keys, types, strict=False)))
    # the types of vals are in types, and they are zipped in the same way with
    # the keys as the vals are zipped here so this should actually be safe.
    return map_type(**dict(zip(keys, vals, strict=False))), map_type  # type: ignore[typeddict-item]


def _random_named_tuple(size: int, factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[NamedTupleTarget_co, type[NamedTupleTarget_co]]:
    vals, types = _random_values(size, factories)
    keys = [_random_symbol() for _ in vals]
    # Functional syntax to construct NamedTuple classes -> _make exists
    namedtuple_type = \
        cast("type[NamedTupleTarget_co]",
             NamedTuple(_random_symbol(), list(zip(keys, types, strict=False))))
    # _make is actually public
    # noinspection PyProtectedMember
    return namedtuple_type._make(vals), namedtuple_type  # pylint: disable=no-member


def _random_dataclass(size: int, factories: Sequence[ObjectFactory[Any]]) \
        -> tuple[DataclassTarget_co, type[DataclassTarget_co]]:
    vals, types = _random_values(size, factories)
    keys = [_random_symbol() for _ in vals]
    dataclass_type = make_dataclass(_random_symbol(), list(zip(keys, types, strict=False)))
    # dataclass_type is a dataclass-type as it was created with make_dataclass
    # noinspection PyTypeChecker
    return dataclass_type(**dict(zip(keys, vals, strict=False))), dataclass_type


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
        "tuple[Sequence[_T], Sequence[type[_T]]]",
        tuple(zip(*(add_to_previous(val, ty) for val, ty in values_with_types if
              cannot_convert_to_previous_type(val)), strict=False)))
    return value_and_types or ((), ())


class _StringToFloat(FromJsonConverter[float, None]):

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[float]) -> bool:
        return isinstance(js, str) and issubclass(float, target_type_info.full_type)

    def convert(self, js: Json, target_type_info: ParameterizedTypeInfo[float], path: JsonPath,
                from_json: Callable[[Json, type[None], JsonPath], None]) -> float:
        if isinstance(js, str):
            return float(js)
        raise FromJsonConversionError(js, path, target_type_info.full_type,
                                      "Can only convert str to float")


class _FloatToString(ToJsonConverter[float]):

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, float)

    def convert(self, o: SourceType_contra, to_json: Callable[[Any], Json]) -> Json:
        return str(o)
