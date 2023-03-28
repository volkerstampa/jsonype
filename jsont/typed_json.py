from inspect import isclass, get_annotations
from types import NoneType
from typing import Any, Union, Sequence, Mapping, Type, TypeVar, get_origin, get_args, Callable, Iterable, Tuple, cast, \
    List

JsonNull = NoneType
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]

T = TypeVar("T")
S = TypeVar("S")
LI = TypeVar("LI", bound=Sequence)
R = TypeVar("R")

NO_SUCCESS = object()


def first_success(f: Callable[..., R], i: Iterable[Tuple]) -> Tuple[Union[R, object], Sequence[ValueError]]:
    failures: List[ValueError] = []
    for args in i:
        try:
            return f(*args), failures
        except ValueError as e:
            failures.append(e)
            pass
    return NO_SUCCESS, failures


class TypedJson:

    def to_json(self, o: Any) -> Json:
        if isinstance(o, JsonNull):
            return self._null_to_json(o)
        if isinstance(o, JsonSimple):
            return self._simple_to_json(o)
        if isinstance(o, Sequence):
            return self._sequence_to_json(o)
        if isinstance(o, Mapping):
            return self._mapping_to_json(o)
        raise ValueError(f"{o} of type {type(o)} no yet supported")

    def from_json(self, js: Json, cl: Type[T]) -> T:
        origin_of_generic = get_origin(cl)
        annotations = get_annotations(cl)
        if cl is Any:
            return js
        if origin_of_generic is Union:
            return self._union_from_json(js, cl)
        if cl is JsonNull:
            return self._null_from_json(js)
        if isclass(cl) and issubclass(cl, JsonSimple):
            return self._simple_from_json(js, cl)
        if isclass(origin_of_generic) and issubclass(origin_of_generic, tuple):
            return self._tuple_from_json(js, cl)
        if isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Sequence):
            return self._sequence_from_json(js, cl)
        if isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Mapping):
            return self._mapping_from_json(js, cl)
        if isclass(cl) and issubclass(cl, Mapping):
            return self._typed_mapping_from_json(js, cl, annotations)
        raise ValueError(f"{cl}{f' ({origin_of_generic})' if origin_of_generic else ''} as target type not supported")

    @staticmethod
    def _simple_to_json(js: JsonSimple) -> Json:
        return js

    @staticmethod
    def _simple_from_json(js: JsonSimple, cl: Type[JsonSimple]) -> Json:
        if isinstance(js, cl):
            return cl(js)
        raise ValueError(f"Cannot convert {js} to {cl}")

    @staticmethod
    def _null_to_json(o: JsonNull) -> JsonNull:
        return cast(JsonNull, None)

    @staticmethod
    def _null_from_json(js: Any) -> None:
        if isinstance(js, JsonNull):
            return None
        raise ValueError(f"Cannot convert {js} to None")

    def _union_from_json(self, js: Json, cl: Type[T]) -> T:
        union_types = get_args(cl)
        # a str is also a Sequence of str so check str first to avoid that
        # it gets converted to a Sequence of str
        union_types_with_str_first = ([str] if str in union_types else []) + [ty for ty in union_types if ty is not str]
        res, failures = first_success(self.from_json, ((js, ty) for ty in union_types_with_str_first))
        if res != NO_SUCCESS:
            return res
        raise ValueError(f"Cannot convert {js} to any of {union_types_with_str_first}: "
                         f"{list(zip(union_types_with_str_first, failures))}")

    def _sequence_to_json(self, li: Sequence[Any]) -> Sequence[Json]:
        return [self.to_json(e) for e in li]

    def _tuple_from_json(self, js: Json, cl: Type[T]) -> T:
        element_types = get_args(cl)
        if element_types.count(...) > 1:
            raise ValueError(f"Cannot convert {js} to {cl} as {cl} has more than one ... parameter")
        if isinstance(js, Sequence):
            element_types = replace_ellipsis(element_types, len(js))
            if len(js) != len(element_types):
                raise ValueError(f"Cannot convert {js} to {cl} as number of type parameter do not match")
            return tuple(self.from_json(e, ty) for e, ty in zip(js, element_types))
        raise ValueError(f"Cannot convert {js} to {cl} as types are not convertible")

    def _sequence_from_json(self, js: Json, cl: Type[T]) -> T:
        element_types = get_args(cl) or (Any,)
        assert len(element_types) == 1
        if isinstance(js, Sequence):
            return [self.from_json(e, element_types[0]) for e in js]
        raise ValueError(f"Cannot convert {js} to {cl}")

    def _mapping_to_json(self, o: Mapping[Any, Any]) -> Mapping[str, Json]:
        def ensure_str(k: Any) -> str:
            if isinstance(k, str):
                return k
            raise ValueError(f"Cannot convert {o} to json as it contains a non-str key: {k}")

        return {ensure_str(k): self.to_json(v) for k, v in o.items()}

    def _mapping_from_json(self, js: Json, cl: Type[T]) -> T:
        key_value_types = get_args(cl) or (str, Any)
        key_type, value_type = key_value_types
        if key_type is not str:
            raise ValueError(f"Cannot convert {js} to mapping with key-type: {key_type}")
        if isinstance(js, Mapping):
            return {k: self.from_json(v, value_type) for k, v in js.items()}
        raise ValueError(f"Cannot convert {js} to {cl}")

    def _typed_mapping_from_json(self, js: Json, cl: Type[T], annotations: Mapping[str, type]) -> T:
        def type_for_key(k: str) -> type:
            t = annotations.get(k)
            if t:
                return t
            raise ValueError(f"Cannot convert {js} to {cl} as it contains unknown key {k}")

        if isinstance(js, Mapping):
            if cl.__required_keys__.issubset(frozenset(js.keys())):
                return {k: self.from_json(v, type_for_key(k)) for k, v in js.items()}  # type: ignore
            raise ValueError(f"Cannot convert {js} to {cl} "
                             f"as it does not contain all required keys {cl.__required_keys__}")
        raise ValueError(f"Cannot convert {js} to {cl}")


def replace_ellipsis(element_types: Sequence[Type[T]], expected_len: int) -> Sequence[Type[T]]:
    if ... in element_types:
        element_types = fill_ellipsis(element_types, expected_len, Any)
    return element_types


def fill_ellipsis(types: Sequence[Type[T]], expected_len: int, fill_type: Type[T]) -> Sequence[Type[T]]:
    types = list(types)
    ellipsis_idx = types.index(...)
    types[ellipsis_idx:ellipsis_idx+1]=[fill_type] * (expected_len - len(types) + 1)
    return types

