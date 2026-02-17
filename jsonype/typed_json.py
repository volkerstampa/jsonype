from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar, cast

from jsonype.base_types import Json, JsonPath, Options
from jsonype.basic_from_json_converters import (FromJsonConversionError, FromJsonConverter,
                                                ParameterizedTypeInfo, ToAny, ToList, ToLiteral,
                                                ToMapping, ToNone, ToSimple, ToTuple,
                                                ToTypedMapping, ToUnion)
from jsonype.basic_to_json_converters import (FromMapping, FromNone, FromSequence, FromSimple,
                                              ToJsonConverter, UnsupportedSourceTypeError)
from jsonype.dataclass_converters import FromDataclass, ToDataclass
from jsonype.named_tuple_converters import FromNamedTuple, ToNamedTuple
from jsonype.simple_str_based_converters import (FromBytes, FromPath, FromUrl, FromUUID, ToBytes,
                                                 ToPath, ToUrl, ToUUID)
from jsonype.time_converters import FromDate, FromDatetime, FromTime, ToDate, ToDatetime, ToTime

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from jsonype.basic_to_json_converters import ContainerElementToJson

TargetType = TypeVar("TargetType")
JsonType = TypeVar("JsonType")


class TypedJson:
    """Provides methods to convert python objects to/from a JSON-representation.

    Args;
        strict: Perform a strict from-JSON conversion.
            This makes :meth:`from_json` raise more
            often for example when extra fields are in the JSON-representation that do not
            exist in the target-type.

    Example: TypedJson
        >>> from dataclasses import dataclass
        >>> from typing import NamedTuple
        >>> from jsonype import TypedJson, FromJsonConversionError, JsonPath
        >>> from json import dumps, loads
        >>>
        >>> # Create TypedJson instance
        >>> typed_json = TypedJson.default()
        >>>
        >>> # Define your types with type-hints
        >>> class Address(NamedTuple):
        ...     street: str
        ...     city: str
        ...     some_related_number: int
        >>>
        >>> @dataclass
        ... class Person:
        ...     name: str
        ...     address: Address
        >>>
        >>> # Parse JSON string with python's json package
        >>> js = loads('''{
        ...         "name": "John Doe",
        ...         "address": {
        ...             "street": "123 Maple Street",
        ...             "city": "Any town",
        ...             "some_related_number": 5,
        ...             "zip": "ignored"
        ...         }
        ...     }''')
        >>> # convert generic representation to your type
        >>> person = typed_json.from_json(js, Person)
        >>>
        >>> assert person == Person(
        ...     name="John Doe",
        ...     address=Address(
        ...         street="123 Maple Street",
        ...         city="Any town",
        ...         some_related_number=5
        ...     ),
        ... )
        >>>
        >>> try:
        ...     # strict conversion does not accept extra fields in the JSON-object
        ...     person = TypedJson.default(strict=True).from_json(js, Person)
        ... except FromJsonConversionError as e:
        ...     print(e)  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        ("Cannot convert {'street': '...', ..., 'zip': 'ignored'} (type: <class 'dict'>)
        at $.address to <class 'Address'>: unexpected keys: {'zip'}", ...
        >>>
        >>> # JSON-types must match expected types:
        >>> # FromJsonConversionError contains path where the error occurred.
        >>> js = loads('''{
        ...         "name": "John Doe",
        ...         "address": {
        ...             "street": "123 Maple Street",
        ...             "city": "Any town",
        ...             "some_related_number": "5"
        ...         }
        ...     }''')
        >>> try:
        ...     person = typed_json.from_json(js, Person)
        ... except FromJsonConversionError as e:
        ...     print(e)  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        ...     assert e.path == JsonPath(("address", "some_related_number"))
        ("Cannot convert 5 (type: <class 'str'>)
        at $.address.some_related_number to <class 'int'>...", ...
        >>> # Convert typed objects to JSON
        >>> print(dumps(typed_json.to_json(person), indent=2))
        {
          "name": "John Doe",
          "address": {
            "street": "123 Maple Street",
            "city": "Any town",
            "some_related_number": 5
          }
        }
    """

    def __init__(self, from_json_converters: Sequence[FromJsonConverter[Any, Any]],
                 to_json_converters: Sequence[ToJsonConverter[Any]]) -> None:
        self._from_json_converters = from_json_converters
        self._to_json_converters = to_json_converters

    def to_json(self, o: Any, opts: Options[Any] | None = None) -> Json:
        """Convert the given object to a JSON-representation.

        The JSON-representation can afterward be converted to a string containing
        JSON by using :func:`json.dumps`.

        Args:
            o: The object to be converted.
            opts: Options or hints for the conversion
        Returns:
            The JSON-representation.
        Raises:
            ValueError: if the object cannot be converted to a JSON-representation
                as no suitable converter exists for the object's type.
        """
        if opts:
            return opts.to_json(o)
        converter = next((conv for conv in self._to_json_converters if
                          conv.can_convert(o)),
                         None)
        if not converter:
            raise UnsupportedSourceTypeError(o)
        # mypy derives a Callable type for self.to_json, but Callables cannot define
        # optional parameters
        return converter.convert(o, cast("ContainerElementToJson", self.to_json))

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
        return self.from_json_with_path(js, target_type, JsonPath())

    def from_json_with_path(
            self, js: Json, target_type: type[TargetType], path: JsonPath
    ) -> TargetType:
        target_type_info = ParameterizedTypeInfo.from_optionally_generic(target_type)
        if target_type_info.opts:
            return target_type_info.opts.from_json(js)
        # According to mypy the type is correct (type | None instead of ParamSpec)
        # noinspection PyTypeChecker
        converter = next((conv for conv in self._from_json_converters if
                          conv.can_convert(js, target_type_info)),
                         None)
        if not converter:
            raise FromJsonConversionError(
                js, path, target_type,
                reason="No suitable converter registered. Use TypedJson.append "
                       "or TypedJson.prepend to register one."
            )
        # converter can_convert from type[T] so it should return T
        return cast("TargetType",
                    converter.convert(js, target_type_info, path, self.from_json_with_path))

    @staticmethod
    def default_converters(
            strict: bool = False
    ) -> tuple[Sequence[FromJsonConverter[Any, Any]], Sequence[ToJsonConverter[Any]]]:
        return (
            (
                ToAny(),
                ToUnion(),
                ToLiteral(),
                ToNone(),
                ToBytes(),
                ToUrl(),
                ToDatetime(),
                ToDate(),
                ToTime(),
                ToUUID(),
                ToPath(),
                ToSimple(),
                ToNamedTuple(strict),
                ToDataclass(),
                ToTuple(),
                ToList(),
                ToTypedMapping(strict),
                ToMapping(),
            ),
            (
                FromNone(),
                FromBytes(),
                FromUrl(),
                FromDatetime(),
                FromDate(),
                FromTime(),
                FromUUID(),
                FromPath(),
                FromSimple(),
                FromNamedTuple(),
                FromDataclass(),
                FromSequence(),
                FromMapping(),
            )
        )

    @classmethod
    def default(cls, strict: bool = False) -> "TypedJson":
        """Create a ``TypedJson`` instance with reasonable default converters.

        Next to straight forward converters for simple types (``str, bool, ...``) and
        simple collections (``list, tuple, Mapping``) the converters support the following
        conversions:

        - :class:`dataclasses.dataclass` to/from ``dict``
        - :class:`typing.NamedTuple` to/from ``dict``
        - various time-related types like :class:`datetime.datetime` to/from ``str``

        The full list of converters is:

        - :class:`ToAny`
        - :class:`ToUnion`
        - :class:`ToLiteral`
        - :class:`ToNone`
        - :class:`ToBytes`
        - :class:`ToUrl`
        - :class:`ToDatetime`
        - :class:`ToDate`
        - :class:`ToTime`
        - :class:`ToUUID`
        - :class:`ToPath`
        - :class:`ToSimple`
        - :class:`ToNamedTuple`,
        - :class:`ToDataclass`
        - :class:`ToTuple`
        - :class:`ToList`
        - :class:`ToTypedMapping`,
        - :class:`ToMapping`
        - :class:`FromNone`
        - :class:`FromBytes`
        - :class:`FromUrl`
        - :class:`FromDatetime`
        - :class:`FromDate`
        - :class:`FromTime`
        - :class:`FromUUID`
        - :class:`FromPath`
        - :class:`FromSimple`
        - :class:`FromNamedTuple`
        - :class:`FromDataclass`
        - :class:`FromSequence`
        - :class:`FromMapping`

        Args:
            strict: Some of the converters support a strict-mode. For example the converters
                converting to a ``dataclass`` or a ``NamedTuple`` fail in struct mode if the
                JSON object contains additional keys.
        """
        return cls(*TypedJson.default_converters(strict))

    def prepend(self, from_json_converters: Sequence[FromJsonConverter[Any, Any]],
                to_json_converters: Sequence[ToJsonConverter[Any]]) -> "TypedJson":
        """Return a new ``TypedJson`` with the given converters prepended to the existing ones.

        Prepended converters take precedence over existing ones, i.e. if a prepended converter
        converts the same types as an existing one (but differently), the existing one becomes
        ineffective. In case of a ``FromJsonConverter`` both input and output types are considered.

        Args:
            from_json_converters: a list of ``FromJsonConverter`` that are added to the top of the
                list of all ``FromJsonConverter``.
            to_json_converters: a list of ``ToJsonConverter`` that are added to the top of the
                list of all ``ToJsonConverter``.

        Example prepend:
            >>> from dataclasses import dataclass
            >>> from jsonype import TypedJson, FunctionBasedToSimpleJsonConverter
            >>> from json import dumps
            >>>
            >>> class Password(str):
            ...     pass
            >>>
            >>> @dataclass
            ... class Person:
            ...     name: str
            ...     pwd: Password
            >>>
            >>> person = Person("John Doe", Password("secret"))
            >>>
            >>> typed_json = TypedJson.default()
            >>> # The secret is revealed
            >>> print(dumps(typed_json.to_json(person)))
            {"name": "John Doe", "pwd": "secret"}
            >>> # A custom converter can prevent revealing Password types
            >>> # Simple custom converters are most easily built with
            >>> # FunctionBasedFromSimpleJsonConverter or FunctionBasedToSimpleJsonConverter
            >>> password_to_str = FunctionBasedToSimpleJsonConverter(lambda pwd: "***", Password)
            >>> # Since a Password is also a str the new converter needs to take precedence over
            >>> # the existing converter for str, that is why it is prepended.
            >>> typed_json = typed_json.prepend([], [password_to_str])
            >>> print(dumps(typed_json.to_json(person)))
            {"name": "John Doe", "pwd": "***"}
        """
        return TypedJson([*from_json_converters, *self._from_json_converters],
                         [*to_json_converters, *self._to_json_converters])

    def append(self, from_json_converters: Sequence[FromJsonConverter[Any, Any]],
               to_json_converters: Sequence[ToJsonConverter[Any]]) -> "TypedJson":
        """Return a new ``TypedJson`` with the given converters appended to the existing ones.

        Existing converters take precedence over appended ones,  i.e. if an appended converter
        converts the same types as an existing one (but differently), the appended one becomes
        ineffective.

        Args:
            from_json_converters: a list of ``FromJsonConverter`` that are added to the top of the
                list of all ``FromJsonConverter``.
            to_json_converters: a list of ``ToJsonConverter`` that are added to the top of the
                list of all ``ToJsonConverter``.

        Example append:
            >>> from dataclasses import dataclass
            >>> from typing import Callable, Any
            >>> from jsonype import (TypedJson, FromJsonConversionError, FromJsonConverter,
            ...     JsonPath, Json, ParameterizedTypeInfo)
            >>> from json import dumps, loads
            >>>
            >>> # A custom type that needs a custom converter
            >>> class CustomType:
            ...     def __eq__(self, other: Any) -> bool:
            ...         return type(other) == CustomType
            >>>
            >>> @dataclass
            ... class Person:
            ...     name: str
            ...     something_special: CustomType
            >>>
            >>> js = loads('''{
            ...     "name": "John Doe",
            ...     "something_special": "CustomType"
            ... }''')
            >>> typed_json = TypedJson.default()
            >>> # Without custom converter the conversion fails
            >>> try:
            ...     person = typed_json.from_json(js, Person)
            ... except FromJsonConversionError as e:
            ...     print(e)  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
            ("Cannot convert CustomType (type: <class 'str'>) at $.something_special
            to <class 'CustomType'>: No suitable converter registered.
            Use TypedJson.append or TypedJson.prepend to register one.", ...
            >>> # Let's write a custom converter that can convert the String "CustomType" to
            >>> # an instance of the CustomType ...
            >>> class StringToCustomType(FromJsonConverter[CustomType, None]):
            ...
            ...     def can_convert(
            ...         self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
            ...     ) -> bool:
            ...         return (js == CustomType.__name__
            ...             and target_type_info.full_type is CustomType)
            ...
            ...     def convert(self, js: Json, target_type_info: ParameterizedTypeInfo[CustomType],
            ...         path: JsonPath,
            ...         from_json: Callable[[Json, type[None], JsonPath],
            ...         None]
            ...     ) -> CustomType:
            ...         return CustomType()
            >>>
            >>> # ... and create a new TypedJson instance with the converter appended.
            >>> typed_json = typed_json.append([StringToCustomType()], [])
            >>> person = typed_json.from_json(js, Person)
            >>> assert person == Person("John Doe", CustomType())
        """
        return TypedJson([*self._from_json_converters, *from_json_converters],
                         [*self._to_json_converters, *to_json_converters])
