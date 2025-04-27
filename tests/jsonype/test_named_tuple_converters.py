from collections import namedtuple
from typing import Any, NamedTuple

from pytest import fixture, mark, raises

from jsonype import (FromJsonConversionError, JsonPath, ParameterizedTypeInfo, ToNamedTuple,
                     TypedJson)


class Demo(NamedTuple):
    field_a: str
    field_b_with_default: int = 1


@fixture(name="to_named_tuple")
def fixture_to_named_tuple() -> ToNamedTuple[Demo, str]:
    return ToNamedTuple()


@fixture(name="strict_to_named_tuple")
def fixture_strict_to_named_tuple() -> ToNamedTuple[Demo, str]:
    return ToNamedTuple(strict=True)


@fixture(name="demo_named_tuple")
def fixture_demo_named_tuple() -> Demo:
    return Demo("Hello")


@fixture(name="demo_info")
def fixture_demo_info() -> ParameterizedTypeInfo[Demo]:
    # Correct according to mypy
    # noinspection PyTypeChecker
    return ParameterizedTypeInfo.from_optionally_generic(Demo)


# untyped required for tests
UntypedDemo = namedtuple("UntypedDemo", ["field_a"])  # noqa: PYI024


@fixture(name="to_untyped_named_tuple")
def fixture_to_untyped_named_tuple() -> ToNamedTuple[UntypedDemo, Any]:
    return ToNamedTuple()


def test_to_named_tuple_can_convert_with_named_tuple(
        to_named_tuple: ToNamedTuple[Demo, str],
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    assert to_named_tuple.can_convert(None, demo_info)


def test_to_named_tuple_can_convert_with_plain_tuple(
        to_named_tuple: ToNamedTuple[Demo, str]
) -> None:
    assert not to_named_tuple.can_convert(None,
                                          ParameterizedTypeInfo.from_optionally_generic(tuple))


def test_to_named_tuple_convert(
        to_named_tuple: ToNamedTuple[Demo, str],
        typed_json: TypedJson,
        demo_named_tuple: Demo,
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    assert to_named_tuple.convert(
        {**demo_named_tuple._asdict(), "extra": "field"},
        demo_info,
        JsonPath(),
        typed_json.from_json_with_path
    ) == demo_named_tuple


def test_to_named_tuple_convert_with_default_value(
        to_named_tuple: ToNamedTuple[Demo, str],
        typed_json: TypedJson,
        demo_named_tuple: Demo,
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    assert to_named_tuple.convert(
        {"field_a": "Hello", "extra": "field"},
        demo_info,
        JsonPath(),
        typed_json.from_json_with_path
    ) == demo_named_tuple


def test_to_named_tuple_convert_with_missing_field(
        to_named_tuple: ToNamedTuple[Demo, str],
        typed_json: TypedJson,
        demo_named_tuple: Demo,
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    with raises(FromJsonConversionError) as e:
        to_named_tuple.convert({}, demo_info, JsonPath(), typed_json.from_json_with_path)
    # Demo is a NamedTuple and thus has public member _field_defaults
    for missing_key in demo_named_tuple._asdict().keys() - Demo._field_defaults.keys():  # noqa: W0212, E1101
        assert missing_key in str(e.value)


def test_to_named_tuple_strict_convert_with_extra_fields(
        strict_to_named_tuple: ToNamedTuple[Demo, str],
        typed_json: TypedJson,
        demo_named_tuple: Demo,
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    with raises(FromJsonConversionError) as e:
        strict_to_named_tuple.convert(
            {**demo_named_tuple._asdict(), "extra": "field"},
            demo_info,
            JsonPath(),
            typed_json.from_json_with_path
        )
    assert "extra" in str(e.value)


@mark.parametrize("untyped_demo", [UntypedDemo("str"), UntypedDemo({"key": "value"})])
def test_to_named_tuple_with_untyped_fields(
        to_untyped_named_tuple: ToNamedTuple[UntypedDemo, Any],
        typed_json: TypedJson,
        untyped_demo: UntypedDemo
) -> None:
    # correct according to mypy
    # noinspection PyTypeChecker
    assert to_untyped_named_tuple.convert(
        untyped_demo._asdict(),
        ParameterizedTypeInfo.from_optionally_generic(UntypedDemo),
        JsonPath(),
        typed_json.from_json_with_path,
    ) == untyped_demo
