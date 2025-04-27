# pylint: disable=W0621
from datetime import datetime, timezone

from pytest import fixture, raises

from jsonype import (FromDatetime, FromJsonConversionError, FromJsonConverter, JsonPath,
                     ParameterizedTypeInfo, ToDatetime, ToJsonConverter, TypedJson)


@fixture
def to_datetime() -> FromJsonConverter[datetime, None]:
    return ToDatetime()


@fixture
def from_datetime() -> ToJsonConverter[datetime]:
    return FromDatetime()


@fixture
def datetime_type_info() -> ParameterizedTypeInfo[datetime]:
    # correct according to mypy
    # noinspection PyTypeChecker
    return ParameterizedTypeInfo.from_optionally_generic(datetime)


@fixture
def timestamp() -> datetime:
    return datetime.now(timezone.utc)


@fixture
def json_path() -> JsonPath:
    return JsonPath().append("here")


def test_to_datetime_can_convert_str(
        to_datetime: FromJsonConverter[datetime, None],
        datetime_type_info: ParameterizedTypeInfo[type[datetime]]
) -> None:
    assert to_datetime.can_convert("", datetime_type_info)


def test_to_datetime_convert_from_str(to_datetime: FromJsonConverter[datetime, None],
                                      timestamp: datetime,
                                      datetime_type_info: ParameterizedTypeInfo[datetime],
                                      typed_json: TypedJson) -> None:
    # Correct according to mypy
    # noinspection PyTypeChecker
    result = to_datetime.convert(
        timestamp.isoformat(), datetime_type_info, JsonPath(), typed_json.from_json_with_path)

    assert result == timestamp


def test_to_datetime_convert_from_broken_str(
        to_datetime: FromJsonConverter[datetime, None],
        datetime_type_info: ParameterizedTypeInfo[datetime],
        json_path: JsonPath,
        typed_json: TypedJson
) -> None:
    with raises(FromJsonConversionError) as e:
        # Correct according to mypy
        # noinspection PyTypeChecker
        to_datetime.convert(
            "broken-str", datetime_type_info, json_path, typed_json.from_json_with_path)

    assert e.value.path == json_path
    assert "invalid isoformat" in str(e.value).lower()


def test_from_datetime_can_convert(
        from_datetime: ToJsonConverter[datetime], timestamp: datetime
) -> None:
    assert from_datetime.can_convert(timestamp)
    assert not from_datetime.can_convert(1)


def test_from_datetime_convert(
        from_datetime: ToJsonConverter[datetime], timestamp: datetime, typed_json: TypedJson
) -> None:
    assert from_datetime.convert(timestamp, typed_json.to_json) == timestamp.isoformat()
