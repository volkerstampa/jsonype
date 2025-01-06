from pytest import fixture

from jsonype import TypedJson


@fixture
def typed_json() -> TypedJson:
    return TypedJson.default()


@fixture
def strict_typed_json() -> TypedJson:
    return TypedJson.default(strict=True)
