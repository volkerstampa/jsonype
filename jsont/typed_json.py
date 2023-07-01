from inspect import get_annotations
from typing import Any, Mapping, Sequence, Type, TypeVar, get_origin

from jsont.base_types import Json, JsonNull, JsonSimple
from jsont.basic_from_json_converters import (ToAny, ToLiteral, ToMapping, ToNone, ToSequence,
                                              ToSimple, ToTuple, ToTypedMapping, ToUnion)
from jsont.basic_to_json_converters import FromMapping, FromNull, FromSequence, FromSimple

T = TypeVar("T")


class TypedJson:

    def __init__(self):
        self._from_json_converters = (
            ToAny(),
            ToUnion(),
            ToLiteral(),
            ToNone(),
            ToSimple(),
            ToTuple(),
            ToSequence(),
            ToMapping(),
            ToTypedMapping(),
        )
        self._to_json_converters = (
            FromNull(),
            FromSimple(),
            FromSequence(),
            FromMapping(),
        )

    def to_json(self, o: Any) -> Json:
        converter = next((conv for conv in self._to_json_converters if
                          conv.can_convert(o)),
                         None)
        if not converter:
            raise ValueError(f"{o} of type {type(o)} cannot be converted to Json")
        return converter.convert(o, self.to_json)

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
