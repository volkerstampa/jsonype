from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, Signature, get_annotations, isclass, signature
from types import NoneType, UnionType
from typing import (Annotated, Any, Generic, Literal, Protocol, TypeVar, Union, cast, get_args,
                    get_origin, runtime_checkable)

from jsonype.base_types import Json, JsonPath, JsonSimple, Options, opts_from

TargetType_co = TypeVar("TargetType_co", covariant=True)
ContainedTargetType_co = TypeVar("ContainedTargetType_co", covariant=True)
JsonType_contra = TypeVar("JsonType_contra", bound=JsonSimple, contravariant=True)


class FromJsonConversionError(ValueError):
    def __init__(
            self, js: Json, path: JsonPath, target_type: type, reason: str | None = None
    ) -> None:
        self._path = path
        super().__init__(f"Cannot convert {js} (type: {type(js)}) at {path} "
                         f"to {target_type}{f': {reason}' if reason else ''}",
                         js, target_type)

    @property
    def path(self) -> JsonPath:
        return self._path


def unnotate(ty: type[TargetType_co], origin: type | None) -> type[TargetType_co]:
    # Annotated is a Callable and yes we want to compare against it
    return (getattr(ty, "__origin__", ty) if origin is Annotated  # type: ignore[comparison-overlap]
            else ty)


@dataclass(frozen=True)
class ParameterizedTypeInfo(Generic[TargetType_co]):
    """Information about a parameterized type.

    Args:
        full_type: full type information, for example ``Mapping[str, int]``.
        origin_of_generic: the unsubscripted version of ``full_type``
            (i.e. without its type parameters), for example ``Mapping``.
            ``None`` if ``full_type`` is not a generic type.
            Can be computed with :func:`typing.get_origin`.
        annotations: a mapping from member name to its type. Can be computed with
            :func:``typing.get_annotations``.
        generic_args: just the arguments of the generic type as a tuple, for example ``(str, int)``.
            ``()`` if ``full_type`` is not a generic type.
            Can be computed with :func:`typing.get_args`.
        opts: First Options instance found in metadata if ``full_type`` is ``Annotated``.
    """

    full_type: type[TargetType_co]
    origin_of_generic: type | None
    annotations: Mapping[str, type]
    generic_args: Sequence[type]
    opts: Options[TargetType_co] | None

    @classmethod
    def from_optionally_generic(
            cls, t: type[TargetType_co]
    ) -> "ParameterizedTypeInfo[TargetType_co]":
        origin = get_origin(t)
        # mypy is fine with this
        # noinspection PyTypeChecker
        return cls(
            unnotate(t, origin),
            origin,
            get_annotations(t) if isclass(t) else {},
            get_args(t),
            opts_from(t),
        )


class FromJsonConverter(ABC, Generic[TargetType_co, ContainedTargetType_co]):
    """The base-class for converters that convert from objects representing JSON.

    Converters that convert from objects representing JSON to their specific python object have to
    implement the two abstract methods defined in this base-class.

    TargetType:
        The type this converter converts objects representing JSON to.

    ContainedTargetType:
        If ``TargetType`` is a container type (like ``Sequence`` for example)
        this is the type of the objects the container contains (e.g. the type of the elements
        of a ``Sequence``).
    """

    @abstractmethod
    def can_convert(self, js: Json, target_type_info: ParameterizedTypeInfo[Any]) -> bool:
        """Return if this converts the given JSON representation into the given target-type.

        Args:
            js: the object representing JSON to be converted
            target_type_info: Describes the target-type of the conversion.
        Returns:
            ``True`` if this converter can convert ``js`` into ``target_type``, ``False`` otherwise.
        """

    @abstractmethod
    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[TargetType_co],
            path: JsonPath,
            from_json: Callable[[Json, type[ContainedTargetType_co], JsonPath],
                                ContainedTargetType_co]
    ) -> TargetType_co:
        """Convert the given object representing JSON to the given target type.

        Args:
            js: the JSON-representation to convert
            target_type_info: describes the type to convert to
            path: the accumulated path where ``js`` stems from. If this is a top-level conversion
                the path is empty (``JsonPath()``) otherwise it denotes the JSON element
                where the fragment ``js`` is located in the JSON that was passed top-level,
                E.g. if ``js`` is the ``1`` in ``{"a": [1]}`` the path is ``JsonPath(("a", 0))``.
            from_json: If this converter converts into container types like :class:`typing.Sequence`
                this function is used to convert the contained JSON-nodes into their respective
                target-types.
        Returns:
            the converted object of type ``target_type``
        Raises:
            ValueError: If the JSON-representation cannot be converted an instance of
                ``target_type``.
        """


class FunctionBasedFromSimpleJsonConverter(FromJsonConverter[TargetType_co, None]):
    """A function based :class:`FromJsonConverter`.

    Creates a ``FromJsonConverter`` from a function that maps a simple JSON type to a target type.

    Args:
        f: A function that maps a simple JSON type (int, float, str, bool) into a target type.
        input_type: None, if the JSON type can be derived from the function signature
            (using :func:`inspect.signature`) or the concrete simple JSON type if this is not
            possible.
        output_type: None if the target type can be derived from the function signature
            (using :func:`inspect.signature`) or the concrete target type if this is not
            possible.

        Example FunctionBasedFromSimpleJsonConverter:
            >>> from typing import Sequence
            >>> from jsonype import (FunctionBasedFromSimpleJsonConverter, ParameterizedTypeInfo,
            ...                      JsonPath)
            >>>
            >>> def str_to_list(comma_separated_str: str) -> Sequence[str]:
            ...     return comma_separated_str.split(",")
            >>>
            >>> converter = FunctionBasedFromSimpleJsonConverter(str_to_list)
            >>> print(converter.convert(
            ...     "a,b",
            ...     ParameterizedTypeInfo.from_optionally_generic(Sequence[str]),
            ...     JsonPath(),
            ...     lambda a, b, c: None
            ... ))
            ['a', 'b']
            >>> # if the function signature is untyped, types can be provided explicitly:
            >>>
            >>> converter2 = FunctionBasedFromSimpleJsonConverter(
            ...     lambda s: s.split(","), str, Sequence[str])
    """

    def __init__(self,
                 f: Callable[[JsonType_contra], TargetType_co],
                 input_type: type[JsonType_contra] | None = None,
                 output_type: type[TargetType_co] | None = None) -> None:
        self._f = f

        if input_type:
            self._input_type = input_type
        if output_type:
            self._output_type = output_type
        if input_type and output_type:
            return
        sig = signature(f)
        if not input_type:
            assert len(sig.parameters) == 1
            input_parameter = next(iter(sig.parameters.values()))
            assert input_parameter.annotation != Parameter.empty
            self._input_type = input_parameter.annotation
        if not output_type:
            assert sig.return_annotation != Signature.empty
            self._output_type = sig.return_annotation

    def can_convert(self, js: Json, target_type_info: ParameterizedTypeInfo[Any]) -> bool:
        return isinstance(js, self._input_type) and target_type_info.full_type is self._output_type

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[TargetType_co],
                path: JsonPath,
                _from_json: Callable[
                    [Json, type[ContainedTargetType_co], JsonPath], ContainedTargetType_co
                ]) -> TargetType_co:
        try:
            assert isinstance(js, self._input_type)
            return self._f(js)
        except ValueError as e:
            raise FromJsonConversionError(js, path, self._output_type, str(e)) from e


class ToAny(FromJsonConverter[Any, None]):
    """Convert to the target type :class:`typing.Any`.

    This converter returns the object representing JSON unchanged.
    """

    def can_convert(self, _js: Json, target_type_info: ParameterizedTypeInfo[Any]) -> bool:
        return (target_type_info.full_type is cast("type", Any)
                or target_type_info.full_type is object)

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[Any],
                path: JsonPath,
                from_json: Callable[[Json, type[None], JsonPath], None]) -> Any:
        return js


class ToUnion(FromJsonConverter[TargetType_co, TargetType_co]):
    """Convert to one of the type-parameters of the given ``typing.Union``.

    It tries to convert the object representing JSON to one of the type-parameters
    of the ``Union``-type in the order of their occurrence and returns the
    first successful conversion result. If none is successful it raises a
    :exc:`ValueError`.

    A ``target_type`` like ``Union[int, str]`` can be used to convert
    for example a ``5`` or a ``"Hello World!"``, but will fail to convert
    a ``list``.
    """

    def can_convert(
            self, _js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        # Union is a type-special-form and thus cannot be compared to a type
        return target_type_info.origin_of_generic in [cast("type", Union), UnionType]

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[TargetType_co],
            path: JsonPath,
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> TargetType_co:
        union_types = target_type_info.generic_args
        # a str is also a Sequence of str so check str first to avoid that
        # it gets converted to a Sequence of str
        union_types_with_str_first = (([str] if str in union_types else [])
                                      + [ty for ty in union_types if ty is not str])
        args: Iterable[tuple[Json, type[Json], JsonPath]] = (
            (js, ty, path) for ty in union_types_with_str_first
        )
        res_or_failures = _first_success(from_json, args)
        if res_or_failures \
                and isinstance(res_or_failures, list) \
                and all(isinstance(e, ValueError) for e in res_or_failures):
            raise FromJsonConversionError(
                js, path, target_type_info.full_type,
                str(list(zip(union_types_with_str_first, res_or_failures, strict=False)))
            )
        # here we know that one conversion was successful. As we only convert into the
        # type-parameters of the Union the returned result must be of the Union-type
        return cast("TargetType_co", res_or_failures)


class ToLiteral(FromJsonConverter[TargetType_co, None]):
    """Convert to one of the listed literals.

    Returns the JSON-representation unchanged if it equals one of the literals.

    A ``target_type`` like ``Literal[5, 6]`` can be used to convert
    for example a ``5`` or a ``6``, but not a ``7``.
    """

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        # Literal is a type-special-form and thus cannot be compared to a type
        # generic args of Literal are instances
        return (target_type_info.origin_of_generic is cast("type", Literal)
                and js in target_type_info.generic_args)  # type: ignore[comparison-overlap]

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[TargetType_co],
                path: JsonPath,
                from_json: Callable[[Json, type[None], JsonPath], None]) -> TargetType_co:
        return cast("TargetType_co", js)


class ToNone(FromJsonConverter[None, None]):
    """Return the JSON-representation, if it is ``None``."""

    def can_convert(self, js: Json, target_type_info: ParameterizedTypeInfo[Any]) -> bool:
        return ((target_type_info.full_type is NoneType or target_type_info.full_type is None)
                and js is None)

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[Any],
                path: JsonPath,
                from_json: Callable[[Json, type[None], JsonPath], None]) -> None:
        assert js is None


class ToSimple(FromJsonConverter[TargetType_co, None]):
    """Return the JSON-representation, if it is one of the types ``int, float, str, bool``."""

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        return (isclass(target_type_info.full_type)
                and issubclass(target_type_info.full_type, get_args(JsonSimple))
                and isinstance(js, target_type_info.full_type))

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[TargetType_co],
                path: JsonPath,
                from_json: Callable[[Json, type[None], JsonPath], None]) -> TargetType_co:
        assert isinstance(js, target_type_info.full_type)
        return js


class ToTuple(FromJsonConverter[tuple[Any, ...], Any]):
    """Convert an array to a :class:`tuple`.

    Convert the elements of the array in the corresponding target type given by the type-parameter
    of the :class:`tuple` in the same position as the element. Raises :exc:`ValueError` if
    the number of type-parameters do not match to the number of elements.

    The type-parameters may contain a single ``...`` which is replaced by as many ``Any`` such that
    the number of type-parameters equals the number of elements. So a target type of
    ``tuple[int, ..., str]`` is equivalent to a target type of ``tuple[int, Any, Any, Any, str]``
    if the JSON-representation to be converted is a :class:`typing.Sequence` of 5 elements.

    A target type like ``tuple[int, str]`` can convert for example the list ``[5, "Hello World!"]``
    into the tuple ``(5, "Hello World!")``, but not ``["Hello World!", 5]``
    """

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        return (isclass(target_type_info.origin_of_generic)
                and issubclass(target_type_info.origin_of_generic, tuple)
                and target_type_info.generic_args.count(...) <= 1
                and isinstance(js, Sequence))

    def convert(self,
                js: Json,
                target_type_info: ParameterizedTypeInfo[tuple[Any, ...]],
                path: JsonPath,
                from_json: Callable[[Json, type[Any], JsonPath], Any]) -> tuple[Any, ...]:
        element_types: Sequence[Any] = target_type_info.generic_args
        assert isinstance(js, Sequence)
        element_types = _replace_ellipsis(element_types, len(js))
        if len(js) != len(element_types):
            raise FromJsonConversionError(
                js,
                path,
                target_type_info.full_type,
                f"Number of elements: {len(js)} not equal to tuple-size {len(element_types)}"
            )
        return tuple(from_json(e, ty, path.append(idx))
                     for idx, (e, ty) in enumerate(zip(js, element_types, strict=False)))


class ToList(FromJsonConverter[Sequence[TargetType_co], TargetType_co]):
    """Convert an array to a :class:`typing.Sequence`.

    Convert all elements of the array into the corresponding target type given by the type-parameter
    of the :class:`typing.Sequence`.

    A target type of ``Sequence[int]`` can convert a ``list`` of ``int``,
    but not a ``list`` of ``str``.
    """

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        # either a parameterized Sequence-type with exactly one type parameter
        return (((isclass(target_type_info.origin_of_generic)
                  and issubclass(cast("type", target_type_info.origin_of_generic), Sequence)
                  and target_type_info.generic_args
                  and len(target_type_info.generic_args) == 1)
                 # or a non-parameterized list-type
                 # don't accept any Sequence-types as this would for example accept a
                 # str-target-type but return a list of anys
                 or (isclass(target_type_info.full_type)
                     and issubclass(target_type_info.full_type, list)))
                and isinstance(js, Sequence))

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[Sequence[TargetType_co]],
            path: JsonPath,
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Sequence[TargetType_co]:
        element_types: Any = target_type_info.generic_args or (Any,)
        assert isinstance(js, Sequence)
        return [from_json(e, element_types[0], path.append(i)) for i, e in enumerate(js)]


class ToMapping(FromJsonConverter[Mapping[str, TargetType_co], TargetType_co]):
    """Convert the JSON-representation to a :class:`typing.Mapping`.

    Convert all entries of the given ``Mapping`` (respectively JSON-object) into entries of a
    ``Mapping`` with the given key and value target types.

    A target type of ``Mapping[str, int]`` can convert for example ``{ "key1": 1, "key2": 2 }``.
    """

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        # Either a parameterized Mapping-type with str as key
        return (((isclass(target_type_info.origin_of_generic)
                  and issubclass(cast("type", target_type_info.origin_of_generic), Mapping)
                  and target_type_info.generic_args
                  and target_type_info.generic_args[0] is str)
                 # or a non-parameterized Mapping-type
                 or (isclass(target_type_info.full_type)
                     and issubclass(target_type_info.full_type, Mapping)
                     # prevent that TypedDicts are converted as the returned dict would not
                     # comply with the types.
                     and not isinstance(target_type_info.full_type, HasRequiredKeys)))
                and isinstance(js, Mapping))

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[Mapping[str, TargetType_co]],
            path: JsonPath,
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Mapping[str, TargetType_co]:
        key_value_types = target_type_info.generic_args or (str, Any)
        _, value_type = key_value_types
        assert isinstance(js, Mapping)
        # value_type of a Mapping[str, TargetType] is type[TargetType]
        return {k: from_json(v, cast("type[TargetType_co]", value_type), path.append(k))
                for k, v in js.items()}


@runtime_checkable
class HasRequiredKeys(Protocol):  # pylint: disable=too-few-public-methods
    __required_keys__: frozenset[str]


class ToTypedMapping(FromJsonConverter[Mapping[str, TargetType_co], TargetType_co]):
    """Convert the JSON-representation to a :class:`typing.TypedDict`.

    Convert all entries of the given ``Mepping`` (respectively JSON-object) into entries of a
    ``TypedDict`` with the given key and value target types.

    Args:
        strict: indicates if the conversion of a ``Mapping`` should fail, if it contains more
            keys than the provided target type. Pass ``True`` to make it fail in this case.
            Defaults to ``False``.

    Example:
        >>> from typing import TypedDict
        >>>
        >>> # using the ToTypedMapping converter one can convert for example:
        >>> json_object = {"k1": 1.0, "k2": 2, "unknown-key": "value"}
        >>> # into the following:
        >>> class Map(TypedDict):
        ...     k1: float
        ...     k2: int
        >>> # In this example the result will meet:
        >>> # assert result == {"k1": 1.0, "k2": 2}

    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    def can_convert(
            self, js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        return ((isclass(target_type_info.full_type)
                 and issubclass(target_type_info.full_type, Mapping)
                 and isinstance(target_type_info.full_type, HasRequiredKeys))
                and isinstance(js, Mapping))

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[Mapping[str, TargetType_co]],
            path: JsonPath,
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Mapping[str, TargetType_co]:
        def type_for_key(k: str) -> type[TargetType_co]:
            t = target_type_info.annotations.get(k)
            if t:
                # target_type_info.full_type is a Mapping[str, TargetType_co] so the
                # annotations of the TypedDict must be of type TargetType_co
                return cast("type[TargetType_co]", t)
            raise FromJsonConversionError(js, path, target_type_info.full_type, f"Unknown key: {k}")

        assert isinstance(js, Mapping)
        assert isinstance(target_type_info.full_type, HasRequiredKeys)
        if target_type_info.full_type.__required_keys__.issubset(frozenset(js.keys())):
            items = js.items() if self.strict \
                else [(k, v) for k, v in js.items() if k in target_type_info.annotations]
            return {k: from_json(v, type_for_key(k), path.append(k)) for k, v in items}
        raise FromJsonConversionError(
            js,
            path,
            cast("type", target_type_info),
            f"Required key missing: {target_type_info.full_type.__required_keys__}"
        )


def _first_success(
        f: Callable[..., ContainedTargetType_co],
        i: Iterable[tuple[TargetType_co, type[TargetType_co], JsonPath]]
) -> ContainedTargetType_co | Sequence[ValueError]:
    failures: list[ValueError] = []
    for args in i:
        try:
            return f(*args)
        # we want to catch each failure not just the first
        # so the except must be in the loop's body
        except ValueError as e:  # noqa: PERF203
            failures.append(e)
    return failures


def _replace_ellipsis(element_types: Sequence[Any], expected_len: int) -> Sequence[Any]:
    if ... in element_types:
        element_types = _fill_ellipsis(element_types, expected_len, object)
    return element_types


def _fill_ellipsis(types: Sequence[Any], expected_len: int, fill_type: type[TargetType_co]) \
        -> Sequence[type[TargetType_co]]:
    types = list(types)
    ellipsis_idx = types.index(...)
    types[ellipsis_idx:ellipsis_idx + 1] = [fill_type] * (expected_len - len(types) + 1)
    return types
