from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Mapping, Sequence, TypeVar, get_args

from jsont.base_types import Json, JsonNull, JsonSimple

T = TypeVar("T")


class ToJsonConverter(ABC, Generic[T]):

    @abstractmethod
    def can_convert(self, o: Any) -> bool:
        pass

    @abstractmethod
    def convert(self, o: T, to_json: Callable[[Any], Json]) -> Json:
        pass


class FromNull(ToJsonConverter[JsonNull]):

    def can_convert(self, o: Any) -> bool:
        return o is None

    def convert(self, o: JsonNull, to_json: Callable[[Any], Json]) -> JsonNull:
        return None


class FromSimple(ToJsonConverter[JsonSimple]):

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, get_args(JsonSimple))

    def convert(self, o: JsonSimple, to_json: Callable[[Any], Json]) -> JsonSimple:
        return o


class FromSequence(ToJsonConverter[Sequence[Any]]):

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, Sequence)

    def convert(self, o: Sequence[Any], to_json: Callable[[Any], Json]) -> Json:
        return [to_json(e) for e in o]


class FromMapping(ToJsonConverter[Mapping[Any, Any]]):

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, Mapping)

    def convert(self, o: Mapping[Any, Any], to_json: Callable[[Any], Json]) -> Json:
        def ensure_str(k: Any) -> str:
            if isinstance(k, str):
                return k
            raise ValueError(f"Cannot convert {o} to json as it contains a non-str key: {k}")

        return {ensure_str(k): to_json(v) for k, v in o.items()}
