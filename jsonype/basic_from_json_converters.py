from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from inspect import isclass
from types import NoneType
from typing import (Any, Callable, Generic, Literal, Protocol, TypeVar, Union, cast, get_args,
                    runtime_checkable)

from jsonype import JsonPath
from jsonype.base_types import Json, JsonSimple

TargetType_co = TypeVar("TargetType_co", covariant=True)
ContainedTargetType_co = TypeVar("ContainedTargetType_co", covariant=True)


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


class UnsupportedTargetTypeError(ValueError):
    def __init__(self, target_type: type, reason: str | None = None) -> None:
        super().__init__(
            f"Target type {target_type} is not supported{f': {reason}' if reason else ''}",
            target_type
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
    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        """Return if this converts from an object representing JSON into the given ``target_type``.

        Args:
            target_type: the type this converter may or may not convert an object that represents
                JSON into.
            origin_of_generic: the unsubscripted version of ``target_type`` (i.e. without
                type-parameters). This origin is computed with :func:`typing.get_origin`.
        Returns:
            ``True`` if this converter can convert into ``target_type``, ``False`` otherwise.
        """

    @abstractmethod
    def convert(
            self,
            js: Json,
            target_type: type[TargetType_co],
            path: JsonPath,
            annotations: Mapping[str, type],
            from_json: Callable[[Json, type[ContainedTargetType_co], JsonPath],
                                ContainedTargetType_co]
    ) -> TargetType_co:
        """Convert the given object representing JSON to the given target type.

        Args:
            js: the JSON-representation to convert
            target_type: the type to convert to
            path: the accumulated path where ``js`` stems from. If this is a top-level conversion
                the path is empty (``JsonPath()``) otherwise it denotes the JSON element
                where the fragment ``js`` is located in the JSON that was passed top-level,
                E.g. if ``js`` is the ``1`` in ``{"a": [1]}`` the path is ``JsonPath(("a", 0))``.
            annotations: the annotations dict for ``target_type`` as returned by
                :func:`inspect.get_annotations`
            from_json: If this converter converts into container types like :class:`typing.Sequence`
                this function is used to convert the contained JSON-nodes into their respective
                target-types.
        Returns:
            the converted object of type ``target_type``
        Raises:
            ValueError: If the JSON-representation cannot be converted an instance of
                ``target_type``.
        """


class ToAny(FromJsonConverter[Any, None]):
    """Convert to the target type :class:`typing.Any`.

    This converter returns the object representing JSON unchanged.
    """

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return target_type is cast(type, Any) or target_type is object

    def convert(self,
                js: Json,
                target_type: type[Any],
                path: JsonPath,
                annotations: Mapping[str, type],
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

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        # Union is a type-special-form and thus cannot be compared to a type
        return origin_of_generic is cast(type, Union)

    def convert(
            self,
            js: Json,
            target_type: type[TargetType_co],
            path: JsonPath,
            annotations: Mapping[str, type],
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> TargetType_co:
        union_types = get_args(target_type)
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
                js, path, target_type,
                str(list(zip(union_types_with_str_first, res_or_failures)))
            )
        # here we know that one conversion was successful. As we only convert into the
        # type-parameters of the Union the returned result must be of the Union-type
        return cast(TargetType_co, res_or_failures)


class ToLiteral(FromJsonConverter[TargetType_co, None]):
    """Convert to one of the listet literals.

    Returns the JSON-representation unchanged if it equals one of the literals, otherwise
    it raises a :exc:`ValueError`

    A ``target_type`` like ``Literal[5, 6]`` can be used to convert
    for example a ``5`` or a ``6``, but not a ``7``.
    """

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        # Literal is a type-special-form and thus cannot be compared to a type
        return origin_of_generic is cast(type, Literal)

    def convert(self,
                js: Json,
                target_type: type[TargetType_co],
                path: JsonPath,
                annotations: Mapping[str, type],
                from_json: Callable[[Json, type[None], JsonPath], None]) -> TargetType_co:
        literals = get_args(target_type)
        if js in literals:
            # as js is one of the literals it must be of the Literal[literals]-type
            return cast(TargetType_co, js)
        raise FromJsonConversionError(js, path, target_type)


class ToNone(FromJsonConverter[None, None]):
    """Return the JSON-representation, if it is ``None``.

    If the given JSON-representation is not ``None`` it raises an :exc:`ValueError`.
    """

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return target_type is NoneType or target_type is None

    def convert(self,
                js: Json,
                target_type: type[Any],
                path: JsonPath,
                annotations: Mapping[str, type],
                from_json: Callable[[Json, type[None], JsonPath], None]) -> None:
        if js is not None:
            raise FromJsonConversionError(js, path, NoneType)


class ToSimple(FromJsonConverter[TargetType_co, None]):
    """Return the JSON-representation, if it is one of the types ``int, float, str, bool``."""

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return isclass(target_type) and issubclass(target_type, get_args(JsonSimple))

    def convert(self,
                js: Json,
                target_type: type[TargetType_co],
                path: JsonPath,
                annotations: Mapping[str, type],
                from_json: Callable[[Json, type[None], JsonPath], None]) -> TargetType_co:
        if isinstance(js, target_type):
            return js
        raise FromJsonConversionError(js, path, target_type)


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

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return isclass(origin_of_generic) and issubclass(origin_of_generic, tuple)

    def convert(self,
                js: Json,
                target_type: type[tuple[Any, ...]],
                path: JsonPath,
                annotations: Mapping[str, type],
                from_json: Callable[[Json, type[Any], JsonPath], Any]) -> tuple[Any, ...]:
        element_types: Sequence[Any] = get_args(target_type)
        if element_types.count(...) > 1:
            raise UnsupportedTargetTypeError(target_type,
                                             "tuple must not have more than one ... parameter")
        if isinstance(js, Sequence):
            element_types = _replace_ellipsis(element_types, len(js))
            if len(js) != len(element_types):
                raise FromJsonConversionError(
                    js,
                    path,
                    target_type,
                    f"Number of elements: {len(js)} not equal to tuple-size {len(element_types)}"
                )
            return tuple(from_json(e, ty, path.append(idx))
                         for idx, (e, ty) in enumerate(zip(js, element_types)))
        raise FromJsonConversionError(js, path, target_type)


class ToList(FromJsonConverter[Sequence[TargetType_co], TargetType_co]):
    """Convert an array to a :class:`typing.Sequence`.

    Convert all elements of the array into the corresponding target type given by the type-parameter
    of the :class:`typing.Sequence`.

    A target type of ``Sequence[int]`` can convert a ``list`` of ``int``,
    but not a ``list`` of ``str``.
    """

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return ((isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Sequence))
                or (isclass(target_type) and issubclass(target_type, Sequence)))

    def convert(
            self,
            js: Json,
            target_type: type[Sequence[TargetType_co]],
            path: JsonPath,
            annotations: Mapping[str, type],
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Sequence[TargetType_co]:
        element_types = get_args(target_type) or (Any,)
        assert len(element_types) == 1
        if isinstance(js, Sequence):
            return [from_json(e, element_types[0], path.append(i)) for i, e in enumerate(js)]
        raise FromJsonConversionError(js, path, target_type)


class ToMapping(FromJsonConverter[Mapping[str, TargetType_co], TargetType_co]):
    """Convert the JSON-representation to a :class:`typing.Mapping`.

    Convert all entries of the given ``Mapping`` (respectively JSON-object) into entries of a
    ``Mapping`` with the given key and value target types.

    A target type of ``Mapping[str, int]`` can convert for example ``{ "key1": 1, "key2": 2 }``.
    """

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return ((isclass(origin_of_generic) and issubclass(cast(type, origin_of_generic), Mapping))
                or (isclass(target_type) and issubclass(target_type, Mapping)
                    and not isinstance(target_type, HasRequiredKeys)))

    def convert(
            self,
            js: Json,
            target_type: type[Mapping[str, TargetType_co]],
            path: JsonPath,
            annotations: Mapping[str, type],
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Mapping[str, TargetType_co]:
        key_value_types = get_args(target_type) or (str, Any)
        key_type, value_type = key_value_types
        if key_type is not str:
            raise UnsupportedTargetTypeError(target_type, "Mapping must have str key-type")
        if isinstance(js, Mapping):
            return {k: from_json(v, value_type, path.append(k)) for k, v in js.items()}
        raise FromJsonConversionError(js, path, target_type)


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
        >>> json_object = {"k1": 1.0, "k2": 2, "un": "known"}
        >>> # into the following:
        >>> class Map(TypedDict):
        ...     k1: float
        ...     k2: int
        >>> # In this example the result will meet:
        >>> # assert result == {"k1": 1.0, "k2": 2}

    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    def can_convert(self, target_type: type, origin_of_generic: type | None) -> bool:
        return (isclass(target_type) and issubclass(target_type, Mapping)
                and isinstance(target_type, HasRequiredKeys))

    def convert(
            self,
            js: Json,
            target_type: type[Mapping[str, TargetType_co]],
            path: JsonPath,
            annotations: Mapping[str, type[TargetType_co]],
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> Mapping[str, TargetType_co]:
        def type_for_key(k: str) -> type[TargetType_co]:
            t = annotations.get(k)
            if t:
                return t
            raise FromJsonConversionError(js, path, target_type, f"Unknown key: {k}")

        if isinstance(js, Mapping) and isinstance(target_type, HasRequiredKeys):
            if target_type.__required_keys__.issubset(frozenset(js.keys())):
                items = js.items() if self.strict \
                    else [(k, v) for k, v in js.items() if k in annotations]
                return {k: from_json(v, type_for_key(k), path.append(k)) for k, v in items}
            raise FromJsonConversionError(js, path, cast(type, target_type),
                                          f"Required key missing: {target_type.__required_keys__}")
        raise FromJsonConversionError(js, path, target_type)


def _first_success(
        f: Callable[..., ContainedTargetType_co],
        i: Iterable[tuple[TargetType_co, type[TargetType_co], JsonPath]]
) -> Union[ContainedTargetType_co, Sequence[ValueError]]:
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
