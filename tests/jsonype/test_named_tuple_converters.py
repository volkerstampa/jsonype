from collections import namedtuple
from inspect import get_annotations
from typing import Any, NamedTuple

from pytest import fixture, mark, raises

from jsonype import TypedJson
from jsonype.basic_from_json_converters import FromJsonConversionError
from jsonype.named_tuple_converters import ToNamedTuple


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


# untyped required for tests
UntypedDemo = namedtuple("UntypedDemo", ["field_a"])  # noqa: PYI024


@fixture(name="to_untyped_named_tuple")
def fixture_to_untyped_named_tuple() -> ToNamedTuple[UntypedDemo, Any]:
    return ToNamedTuple()


def test_to_named_tuple_can_convert_with_named_tuple(
        to_named_tuple: ToNamedTuple[Demo, str]
) -> None:
    assert to_named_tuple.can_convert(Demo, None)


def test_to_named_tuple_can_convert_with_plain_tuple(
        to_named_tuple: ToNamedTuple[Demo, str]
) -> None:
    assert not to_named_tuple.can_convert(tuple, str)


def test_to_named_tuple_convert(
        to_named_tuple: ToNamedTuple[Demo, str], typed_json: TypedJson, demo_named_tuple: Demo
) -> None:
    assert to_named_tuple.convert(
        {**demo_named_tuple._asdict(), "extra": "field"},
        Demo,
        get_annotations(Demo),
        typed_json.from_json
    ) == demo_named_tuple


def test_to_named_tuple_convert_with_default_value(
        to_named_tuple: ToNamedTuple[Demo, str], typed_json: TypedJson, demo_named_tuple: Demo
) -> None:
    assert to_named_tuple.convert(
        {"field_a": "Hello", "extra": "field"},
        Demo,
        get_annotations(Demo),
        typed_json.from_json
    ) == demo_named_tuple


def test_to_named_tuple_convert_with_missing_field(
        to_named_tuple: ToNamedTuple[Demo, str], typed_json: TypedJson, demo_named_tuple: Demo
) -> None:
    with raises(FromJsonConversionError) as e:
        to_named_tuple.convert({}, Demo, get_annotations(Demo), typed_json.from_json)
    # Demo is a NamedTuple and thus has public member _field_defaults
    for missing_key in demo_named_tuple._asdict().keys() - Demo._field_defaults.keys():  # noqa: W0212, E1101
        assert missing_key in str(e.value)


def test_to_named_tuple_strict_convert_with_extra_fields(
        strict_to_named_tuple: ToNamedTuple[Demo, str],
        typed_json: TypedJson,
        demo_named_tuple: Demo
) -> None:
    with raises(FromJsonConversionError) as e:
        strict_to_named_tuple.convert(
            {**demo_named_tuple._asdict(), "extra": "field"},
            Demo,
            get_annotations(Demo),
            typed_json.from_json
        )
    assert "extra" in str(e.value)


@mark.parametrize("untyped_demo", [UntypedDemo("str"), UntypedDemo({"key": "value"})])
def test_to_named_tuple_with_untyped_fields(
        to_untyped_named_tuple: ToNamedTuple[UntypedDemo, Any],
        typed_json: TypedJson,
        untyped_demo: UntypedDemo
) -> None:
    assert to_untyped_named_tuple.convert(
        untyped_demo._asdict(),
        UntypedDemo,
        get_annotations(UntypedDemo),
        typed_json.from_json,
    ) == untyped_demo
