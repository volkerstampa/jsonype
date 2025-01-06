from dataclasses import MISSING, asdict, dataclass, fields

from pytest import fixture, raises

from jsonype import JsonPath, ParameterizedTypeInfo
from jsonype.basic_from_json_converters import FromJsonConversionError
from jsonype.dataclass_converters import FromDataclass, ToDataclass
from jsonype.typed_json import TypedJson


@dataclass
class Demo:
    field_a: str
    field_b_with_default: int = 1


@fixture(name="to_dataclass")
def fixture_to_dataclass() -> ToDataclass[Demo, str]:
    return ToDataclass()


@fixture(name="strict_to_dataclass")
def fixture_strict_to_dataclass() -> ToDataclass[Demo, str]:
    return ToDataclass(strict=True)


@fixture(name="from_dataclass")
def fixture_from_dataclass() -> FromDataclass[Demo]:
    return FromDataclass()


@fixture(name="demo_dataclass")
def fixture_demo_dataclass() -> Demo:
    return Demo("Hello")


@fixture(name="demo_info")
def fixture_demo_info() -> ParameterizedTypeInfo[Demo]:
    # Correct according to mypy
    # noinspection PyTypeChecker
    return ParameterizedTypeInfo.from_optionally_generic(Demo)


def test_to_dataclass_can_convert_with_dataclass(to_dataclass: ToDataclass[Demo, str],
                                                 demo_info: ParameterizedTypeInfo[Demo]) -> None:
    assert to_dataclass.can_convert(None, demo_info)


def test_to_dataclass_can_convert_with_non_dataclass(
    to_dataclass: ToDataclass[Demo, str]
) -> None:
    assert not to_dataclass.can_convert(None, ParameterizedTypeInfo.from_optionally_generic(str))


def test_to_dataclass_convert(to_dataclass: ToDataclass[Demo, str],
                              demo_dataclass: Demo,
                              typed_json: TypedJson,
                              demo_info: ParameterizedTypeInfo[Demo]) -> None:
    # DataclassTarget_co is bound to a Dataclass protocol as suggested here
    # https://github.com/python/mypy/issues/6568#issuecomment-1324196557
    # noinspection PyTypeChecker
    assert to_dataclass.convert(
        {**asdict(demo_dataclass), "extra": "field"},
        demo_info,
        JsonPath(),
        typed_json.from_json_with_path
    ) == demo_dataclass


def test_to_dataclass_convert_with_default(to_dataclass: ToDataclass[Demo, str],
                                           demo_dataclass: Demo,
                                           typed_json: TypedJson,
                                           demo_info: ParameterizedTypeInfo[Demo]) -> None:
    # DataclassTarget_co is bound to a Dataclass protocol as suggested here
    # https://github.com/python/mypy/issues/6568#issuecomment-1324196557
    # noinspection PyTypeChecker
    assert to_dataclass.convert(
        {
            **{field.name: asdict(demo_dataclass)[field.name]
               for field in fields(demo_dataclass)
               if field.default == MISSING},
            "extra": "field"
        },
        demo_info,
        JsonPath(),
        typed_json.from_json_with_path
    ) == demo_dataclass


def test_to_dataclass_convert_with_missing_field(to_dataclass: ToDataclass[Demo, str],
                                                 typed_json: TypedJson,
                                                 demo_info: ParameterizedTypeInfo[Demo]) -> None:
    with raises(FromJsonConversionError) as e:
        # DataclassTarget_co is bound to a Dataclass protocol as suggested here
        # https://github.com/python/mypy/issues/6568#issuecomment-1324196557
        # noinspection PyTypeChecker
        to_dataclass.convert({}, demo_info, JsonPath(), typed_json.from_json_with_path)
    # Demo is a Dataclass
    # noinspection PyTypeChecker
    for field_name in (field.name for field in fields(Demo) if field.default == MISSING):
        assert field_name in str(e.value)


def test_to_dataclass_strict_convert_with_extra_fields(
        strict_to_dataclass: ToDataclass[Demo, str],
        demo_dataclass: Demo,
        typed_json: TypedJson,
        demo_info: ParameterizedTypeInfo[Demo]
) -> None:
    with raises(FromJsonConversionError) as e:
        # DataclassTarget_co is bound to a Dataclass protocol as suggested here
        # https://github.com/python/mypy/issues/6568#issuecomment-1324196557
        # noinspection PyTypeChecker
        strict_to_dataclass.convert(
            {**asdict(demo_dataclass), "extra": "field"},
            demo_info,
            JsonPath(),
            typed_json.from_json_with_path
        )
    assert "extra" in str(e.value)


def test_from_dataclass_can_convert_with_class(from_dataclass: FromDataclass[Demo]) -> None:
    assert not from_dataclass.can_convert(Demo)
