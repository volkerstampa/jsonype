from pytest import raises

from jsonype import FromJsonConversionError, JsonPath, ParameterizedTypeInfo
from jsonype.basic_from_json_converters import FunctionBasedFromSimpleJsonConverter


def test_function_based_from_simple_json_converter() -> None:
    def str_to_int(s: str) -> int:
        return int(s)

    convertable_str = "123"

    converter = FunctionBasedFromSimpleJsonConverter(str_to_int)

    type_info = ParameterizedTypeInfo.from_optionally_generic(int)
    assert converter.can_convert(convertable_str, type_info)
    # correct according to mypy
    # noinspection PyTypeChecker
    assert (converter.convert(convertable_str, type_info, JsonPath(), lambda _a, _b, _c: None)
            == int(convertable_str))


def test_function_based_from_simple_json_converter_with_wrong_input() -> None:
    expected_exception = ValueError("Test-Error")

    def str_to_int(_: str) -> int:
        raise expected_exception

    converter = FunctionBasedFromSimpleJsonConverter(str_to_int)

    type_info = ParameterizedTypeInfo.from_optionally_generic(int)
    assert not converter.can_convert(123, type_info)
    with raises(FromJsonConversionError) as e:
        # correct according to mypy
        # noinspection PyTypeChecker
        converter.convert("123", type_info, JsonPath(), lambda _a, _b, _c: None)
    assert str(expected_exception) in str(e.value)
