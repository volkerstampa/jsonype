from inspect import get_annotations
from typing import Any, TypeVar, cast, get_origin

from jsont.base_types import Json
from jsont.basic_from_json_converters import (FromJsonConverter, ToAny, ToList, ToLiteral,
                                              ToMapping, ToNone, ToSimple, ToTuple, ToTypedMapping,
                                              ToUnion, UnsupportedTargetTypeError)
from jsont.basic_to_json_converters import (FromMapping, FromNone, FromSequence, FromSimple,
                                            ToJsonConverter, UnsupportedSourceTypeError)

TargetType = TypeVar("TargetType")


class TypedJson:
    """Provides methods to convert python objects to/from a JSON-representation.

    Args;
        strict: Perform a strict from-JSON conversion.
            This makes :meth:`from_json` raise more
            often for example when extra fields are in the JSON-representation that do not
            exist in the target-type.

    Example:
        >>> from typing import TypedDict
        >>> from jsont import TypedJson
        >>> from json import loads
        >>>
        >>> typed_json = TypedJson()
        >>>
        >>> class Address(TypedDict):
        ...     street: str
        ...     city: str
        >>>
        >>> class Person(TypedDict):
        ...     name: str
        ...     address: Address
        ...     some_related_number: int
        >>>
        >>> js = loads('''{
        ...         "name": "John Doe",
        ...         "address": {
        ...             "street": "123 Maple Street",
        ...             "city": "Any town",
        ...             "zip": "ignored"
        ...         },
        ...         "some_related_number": 5
        ...     }''')
        >>> person = typed_json.from_json(js, Person)
        >>>
        >>> assert person == {
        ...     "name": "John Doe",
        ...     "address": {
        ...         "street": "123 Maple Street",
        ...         "city": "Any town"
        ...     },
        ...     "some_related_number": 5
        ... }
        >>>
        >>> try:
        ...     person = TypedJson(strict=True).from_json(js, Person)
        ... except ValueError as e:
        ...     print(e)
        Cannot convert {'street': '...', ..., 'zip': 'ignored'}
        to <class 'Address'> as it contains unknown key zip
    """

    def __init__(self, strict: bool = False) -> None:
        self._from_json_converters: tuple[FromJsonConverter[Any, Any], ...] = (
            ToAny(),
            ToUnion(),
            ToLiteral(),
            ToNone(),
            ToSimple(),
            ToTuple(),
            ToList(),
            ToMapping(),
            ToTypedMapping(strict),
        )
        self._to_json_converters: tuple[ToJsonConverter[Any], ...] = (
            FromNone(),
            FromSimple(),
            FromSequence(),
            FromMapping(),
        )

    def to_json(self, o: Any) -> Json:
        """Convert the given object to a JSON-representation.

        The JSON-representation can afterwards be converted to a string containing
        JSON by using :func:`json.dumps`.

        Args:
            o: The object to be converted.
        Returns:
            The JSON-representation.
        Raises:
            ValueError: if the object cannot be converted to a JSON-representation
                as no suitable converter exists for the object's type.
        """
        converter = next((conv for conv in self._to_json_converters if
                          conv.can_convert(o)),
                         None)
        if not converter:
            raise UnsupportedSourceTypeError(o)
        return converter.convert(o, self.to_json)

    def from_json(self, js: Json, target_type: type[TargetType]) -> TargetType:
        """Convert the given JSON-representation to an object of the given type.

        The JSON-representation is typically generated from a JSON string by using
        :func:`json.loads`.

        Args:
            js: the JSON-representation to be converted
            target_type: the type the JSON-representation should be converted to
        Returns:
            the object of the given type
        Raises:
            ValueError: If the JSON-representation cannot be converted as a converter
                fails to convert it to an object of the required type.
        """
        origin_of_generic = get_origin(target_type)
        annotations = get_annotations(target_type) if target_type else {}
        converter = next((conv for conv in self._from_json_converters if
                          conv.can_convert(target_type, origin_of_generic)),
                         None)
        if not converter:
            raise UnsupportedTargetTypeError(target_type)
        # converter can_convert from type[T] so it should return T
        return cast(TargetType, converter.convert(js, target_type, annotations, self.from_json))
