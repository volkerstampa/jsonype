from inspect import get_annotations
from typing import Any, Mapping, Sequence, Type, TypeVar, get_origin

from jsont.base_types import Json, JsonNull, JsonSimple
from jsont.basic_from_json_converters import (ToAny, ToLiteral, ToMapping, ToNone, ToSequence,
                                              ToSimple, ToTuple, ToTypedMapping, ToUnion)
from jsont.basic_to_json_converters import FromMapping, FromNone, FromSequence, FromSimple

T = TypeVar("T")


class TypedJson:
    """Provides methods to convert python objects to/from a json-representation.

    Example:
        >>> from typing import TypedDict
        >>> from jsont.typed_json import TypedJson
        >>>
        >>> typed_json = TypedJson()
        >>>
        >>> class Map(TypedDict):
        ...     k1: float
        ...     k2: int
        >>>
        >>> m = typed_json.from_json(
        ...     {"k1": 1.0, "k2": 2, "un": "known"},
        ...     Map
        ... )
        >>>
        >>> assert m == {"k1": 1.0, "k2": 2}
    """

    def __init__(self, strict: bool = False):
        self._from_json_converters = (
            ToAny(),
            ToUnion(),
            ToLiteral(),
            ToNone(),
            ToSimple(),
            ToTuple(),
            ToSequence(),
            ToMapping(),
            ToTypedMapping(strict),
        )
        self._to_json_converters = (
            FromNone(),
            FromSimple(),
            FromSequence(),
            FromMapping(),
        )

    def to_json(self, o: Any) -> Json:
        """Convert the given object to a json-representation.

        Args:
            o: The object to be converted.
        Returns:
            The json-representation.
        Raises:
            ValueError: if the object cannot be converted to a json-representation
                as no suitable converter exists for the object's type.
        """
        converter = next((conv for conv in self._to_json_converters if
                          conv.can_convert(o)),
                         None)
        if not converter:
            raise ValueError(f"{o} of type {type(o)} cannot be converted to Json")
        return converter.convert(o, self.to_json)

    def from_json(self, js: Json, cl: Type[T]) -> T:
        """Convert the given json-representation to an object of the given type.

        Args:
            js: the json-representation to be converted
            cl: the type the json-representation should be converted to
        Returns:
            the object of the given type
        Raises:
            ValueError: If the json-representation cannot be converted as a converter
                fails to convert it to an object of the required type.
        """
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
