from pytest import fixture

from jsonype import TypedJson


@fixture
def typed_json() -> TypedJson:
    return TypedJson()


@fixture
def strict_typed_json() -> TypedJson:
    return TypedJson(strict=True)
