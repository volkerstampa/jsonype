from typing import Any, Union, Sequence, Mapping, Type, TypeVar, get_origin, get_args, Callable, Iterable, Tuple

JsonNull = type(None)
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]

T = TypeVar("T")
R = TypeVar("R")

NO_SUCCESS = object()


def first_success(f: Callable[..., R], i: Iterable[Tuple]) -> Union[R, object]:
    for args in i:
        try:
            return f(*args)
        except ValueError:
            pass
    return NO_SUCCESS



class TypedJson:

    def to_json(self, o: Any) -> Json:
        if isinstance(o, JsonNull):
            return self._null_to_json(o)
        if isinstance(o, JsonSimple):
            return self._simple_to_json(o)
        raise ValueError(f"{o} of type {type(o)} no yet supported")

    def from_json(self, js: Json, cl: Type[T]) -> T:
        if get_origin(cl) is Union:
            return self._union_from_json(js, cl)
        if issubclass(cl, JsonNull):
            return self._null_from_json(js)
        if issubclass(cl, JsonSimple):
            return self._simple_from_json(js, cl)
        raise ValueError(f"{cl} as target type no yet supported")

    def _union_from_json(self, js: Json, cl: Type[T]) -> T:
        res = first_success(self.from_json, ((js, ty) for ty in get_args(cl)))
        if res != NO_SUCCESS:
            return res
        raise ValueError(f"Cannot convert {js} to any of {get_args((cl))}")



    @staticmethod
    def _simple_to_json(js: JsonSimple) -> Json:
        return js

    @staticmethod
    def _simple_from_json(js: JsonSimple, cl: Type[JsonSimple]) -> Json:
        if isinstance(js, cl):
            return cl(js)
        raise ValueError(f"Cannot convert {js} to {cl}")

    @staticmethod
    def _null_to_json(o: None) -> None:
        return None

    @staticmethod
    def _null_from_json(js: Any) -> None:
        if isinstance(js, JsonNull):
            return None
        raise ValueError(f"{js} cannot be converted to None")
