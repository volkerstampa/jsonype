from typing import Any, Union, Sequence, Mapping, Type, TypeVar

JsonNull = type(None)
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]

T = TypeVar("T")


class TypedJson:

    def to_json(self, o: Any) -> Json:
        if isinstance(o, JsonNull):
            return self._null_to_json(o)
        if isinstance(o, JsonSimple):
            return self._simple_to_json(o)
        raise ValueError(f"{o} of type {type(o)} no yet supported")

    def from_json(self, js: Json, cl: Type[T]) -> T:
        if issubclass(cl, JsonNull):
            return self._null_from_json(js)
        if issubclass(cl, JsonSimple):
            return self._simple_from_json(js, cl)
        raise ValueError(f"{cl} as target type no yet supported")


    @staticmethod
    def _simple_to_json(o: JsonSimple) -> Json:
        return o

    @staticmethod
    def _simple_from_json(o: JsonSimple, cl: Type[JsonSimple]) -> Json:
        return cl(o)

    @staticmethod
    def _null_to_json(o: None) -> None:
        return None

    @staticmethod
    def _null_from_json(js: Any) -> None:
        if isinstance(js, JsonNull):
            return None
        raise ValueError(f"{js} cannot be converted to None")
