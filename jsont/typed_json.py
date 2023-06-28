from abc import ABC, abstractmethod
from inspect import get_annotations, isclass
from types import NoneType
from typing import (Any, Callable, Generic, Iterable, List, Literal, Mapping, Sequence, Tuple, Type,
                    TypeVar, Union, cast, get_args, get_origin)

JsonNull = Literal[None]
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]

T = TypeVar("T")
S = TypeVar("S")
LI = TypeVar("LI", bound=Sequence)
R = TypeVar("R")

NO_SUCCESS = object()


def first_success(f: Callable[..., R], i: Iterable[Tuple]) -> Union[R, Sequence[ValueError]]:
    failures: List[ValueError] = []
    for args in i:
        try:
            return f(*args)
        except ValueError as e:
            failures.append(e)
    return failures


class FromJsonConverter(ABC, Generic[T]):
    @abstractmethod
    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        pass

    @abstractmethod
    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        pass


class ToAny(FromJsonConverter[Any]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return target_type is Any

    def convert(self,
                js: Json,
                cl: Type[Any],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> Any:
        return cast(Any, js)


class ToUnion(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return origin_of_generic is Union

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        union_types = get_args(cl)
        # a str is also a Sequence of str so check str first to avoid that
        # it gets converted to a Sequence of str
        union_types_with_str_first = (([str] if str in union_types else [])
                                      + [ty for ty in union_types if ty is not str])
        res_or_failures = first_success(from_json,
                                        ((js, ty) for ty in union_types_with_str_first))
        if res_or_failures \
                and isinstance(res_or_failures, list) \
                and all(isinstance(e, ValueError) for e in res_or_failures):
            raise ValueError(f"Cannot convert {js} to any of {union_types_with_str_first}: "
                             f"{list(zip(union_types_with_str_first, res_or_failures))}")
        return cast(T, res_or_failures)


class ToLiteral(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return origin_of_generic is Literal

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        literals = get_args(cl)
        if js in literals:
            return cast(T, js)
        raise ValueError(f"Cannot convert {js} to any of {literals}")


class ToNone(FromJsonConverter[None]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return target_type is NoneType or target_type is None

    def convert(self,
                js: Json,
                cl: Type[Any],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> None:
        if js is None:
            return None
        raise ValueError(f"Cannot convert {js} to None")


class ToSimple(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return isclass(target_type) and issubclass(target_type, get_args(JsonSimple))

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        if isinstance(js, cl):
            return js
        raise ValueError(f"Cannot convert {js} to {cl}")


class ToTuple(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return isclass(origin_of_generic) and issubclass(origin_of_generic, tuple)

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        element_types: Sequence[Any] = get_args(cl)
        if element_types.count(...) > 1:
            raise ValueError(f"Cannot convert {js} to {cl} as {cl} has more than one ... parameter")
        if isinstance(js, Sequence):
            element_types = replace_ellipsis(element_types, len(js))
            if len(js) != len(element_types):
                raise ValueError(
                    f"Cannot convert {js} to {cl} as number of type parameter do not match")
            return cast(T, tuple(from_json(e, ty) for e, ty in zip(js, element_types)))
        raise ValueError(f"Cannot convert {js} to {cl} as types are not convertible")


class ToSequence(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Sequence)

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        element_types = get_args(cl) or (Any,)
        assert len(element_types) == 1
        if isinstance(js, Sequence):
            return cast(T, [from_json(e, element_types[0]) for e in js])
        raise ValueError(f"Cannot convert {js} to {cl}")


class ToMapping(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Mapping)

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        key_value_types = get_args(cl) or (str, Any)
        key_type, value_type = key_value_types
        if key_type is not str:
            raise ValueError(f"Cannot convert {js} to mapping with key-type: {key_type}")
        if isinstance(js, Mapping):
            return cast(T, {k: from_json(v, value_type) for k, v in js.items()})
        raise ValueError(f"Cannot convert {js} to {cl}")


class ToTypedMapping(FromJsonConverter[T]):

    def can_convert(self, target_type: type, origin_of_generic: type) -> bool:
        return isclass(target_type) and issubclass(target_type, Mapping)

    def convert(self,
                js: Json,
                cl: Type[T],
                annotations: Mapping[str, type],
                from_json: Callable[[Json, Type[S]], S]) -> T:
        def type_for_key(k: str) -> Type[S]:
            t = annotations.get(k)
            if t:
                return cast(Type[S], t)
            raise ValueError(f"Cannot convert {js} to {cl} as it contains unknown key {k}")

        if isinstance(js, Mapping) and hasattr(cl, "__required_keys__"):
            if cl.__required_keys__.issubset(frozenset(js.keys())):  # type: ignore
                return cast(T, {k: from_json(v, type_for_key(k)) for k, v in js.items()})
            raise ValueError(
                f"Cannot convert {js} to {cl} "
                f"as it does not contain all required keys {cl.__required_keys__}"  # type: ignore
            )
        raise ValueError(f"Cannot convert {js} to {cl}")


class TypedJson:

    def __init__(self):
        self._from_json_converters = [
            ToAny(),
            ToUnion(),
            ToLiteral(),
            ToNone(),
            ToSimple(),
            ToTuple(),
            ToSequence(),
            ToMapping(),
            ToTypedMapping(),
        ]

    def to_json(self, o: Any) -> Json:
        if o is None:
            return self._null_to_json(o)
        if isinstance(o, get_args(JsonSimple)):
            return self._simple_to_json(o)
        if isinstance(o, Sequence):
            return self._sequence_to_json(o)
        if isinstance(o, Mapping):
            return self._mapping_to_json(o)
        raise ValueError(f"{o} of type {type(o)} no yet supported")

    def from_json(self, js: Json, cl: Type[T]) -> T:
        origin_of_generic = get_origin(cl)
        annotations = get_annotations(cl) if cl else {}
        converter = next((conv for conv in self._from_json_converters if
                          conv.can_convert(cl, origin_of_generic)),
                         None)
        if not converter:
            raise ValueError(f"{cl}{f' ({origin_of_generic})' if origin_of_generic else ''} "
                             "as target type not supported")
        return converter.convert(js, cl, annotations, self.from_json)

    @staticmethod
    def _simple_to_json(js: JsonSimple) -> Json:
        return js

    @staticmethod
    def _null_to_json(_o: JsonNull) -> JsonNull:
        return None

    def _sequence_to_json(self, li: Sequence[Any]) -> Sequence[Json]:
        return [self.to_json(e) for e in li]

    def _mapping_to_json(self, o: Mapping[Any, Any]) -> Mapping[str, Json]:
        def ensure_str(k: Any) -> str:
            if isinstance(k, str):
                return k
            raise ValueError(f"Cannot convert {o} to json as it contains a non-str key: {k}")

        return {ensure_str(k): self.to_json(v) for k, v in o.items()}


def replace_ellipsis(element_types: Sequence[Any], expected_len: int) -> Sequence[Any]:
    if ... in element_types:
        element_types = fill_ellipsis(element_types, expected_len, Any)  # type: ignore
    return element_types


def fill_ellipsis(types: Sequence[Any], expected_len: int, fill_type: Type[T]) -> Sequence[Type[T]]:
    types = list(types)
    ellipsis_idx = types.index(...)
    types[ellipsis_idx:ellipsis_idx + 1] = [fill_type] * (expected_len - len(types) + 1)
    return types
