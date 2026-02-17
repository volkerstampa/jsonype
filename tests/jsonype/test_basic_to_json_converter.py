from pytest import raises

from jsonype import FunctionBasedToSimpleJsonConverter, ToJsonConversionError


def test_function_based_from_simple_json_converter() -> None:
    def str_to_int(s: str) -> int:
        return int(s)

    convertable_str = "123"

    converter = FunctionBasedToSimpleJsonConverter(str_to_int)

    assert converter.can_convert(convertable_str)
    assert (converter.convert(convertable_str, lambda _a, _b=None: None) == int(convertable_str))


def test_function_based_from_simple_json_converter_with_wrong_input() -> None:
    expected_exception = ValueError("Test-Error")

    def str_to_int(_: str) -> int:
        raise expected_exception

    converter = FunctionBasedToSimpleJsonConverter(str_to_int)

    assert not converter.can_convert(123)
    with raises(ToJsonConversionError) as e:
        converter.convert("123", lambda _a, _b=None: None)
    assert str(expected_exception) in str(e.value)
