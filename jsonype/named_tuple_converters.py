from collections.abc import Iterable, Mapping
from inspect import isclass
# pyflakes wants NamedTuple to be imported as it's used as bounds-parameter below
# noinspection PyUnresolvedReferences
from typing import (Any, Callable, NamedTuple, Protocol, Self, TypeVar, cast,  # noqa: W0611
                    runtime_checkable)

from jsonype.base_types import Json, JsonPath
from jsonype.basic_from_json_converters import (FromJsonConversionError, FromJsonConverter,
                                                ParameterizedTypeInfo, TargetType_co)
from jsonype.basic_to_json_converters import ToJsonConverter

NamedTupleTarget_co = TypeVar("NamedTupleTarget_co", bound="NamedTuple", covariant=True)
NamedTupleSource_contra = TypeVar("NamedTupleSource_contra", bound="NamedTuple", contravariant=True)


@runtime_checkable
# A NamedTuple only comes with methods starting with _
# (to prevent name clashes)
class _NamedTupleProtocol(Protocol):  # noqa: R0903

    # protocol definition, so unused vars are expected
    def __init__(self, **kwargs: Any) -> None:  # noqa: V107
        ...

    def _replace(self) -> Self:
        ...

    # protocol definition, so unused vars are expected
    def _asdict(self, **kwargs: Any) -> dict[str, Any]:  # noqa: V107
        ...

    @classmethod
    # protocol definition, so unused vars are expected
    def _make(
            cls, _iterable: Iterable[Any]  # noqa: V107
    ) -> Self:
        ...


class ToNamedTuple(FromJsonConverter[NamedTupleTarget_co, TargetType_co]):
    """Convert an object representing JSON to a :class:`typing.NamedTuple`.

    The JSON object is expected to have keys corresponding to the ``NamedTuple`` fields.
    Each value is converted to the corresponding field type. In case of an untyped ``NamedTuple``,
    the field type is assumed to be ``Any``.
    """

    def __init__(self, strict: bool = False) -> None:
        self._strict = strict

    def can_convert(
            self, _js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        return (isclass(target_type_info.full_type)
                and issubclass(target_type_info.full_type, _NamedTupleProtocol))

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[NamedTupleTarget_co],
            path: JsonPath,
            from_json: Callable[[Json, type[TargetType_co], JsonPath], TargetType_co]
    ) -> NamedTupleTarget_co:
        def json_value_or_default(field_name: str) -> Any:
            assert isinstance(js, Mapping)
            # _field_defaults is actually public
            # noinspection PyProtectedMember
            return js.get(field_name,
                          target_type_info.full_type._field_defaults.get(field_name))  # noqa: W0212

        if not isinstance(js, Mapping):
            raise FromJsonConversionError(js, path, target_type_info.full_type)
        if self._strict and (extra_keys := js.keys() - target_type_info.annotations.keys()):
            raise FromJsonConversionError(js, path, target_type_info.full_type,
                                          f"unexpected keys: {extra_keys}")
        # _field_defaults is actually public
        # noinspection PyProtectedMember
        if missing_keys := (target_type_info.annotations.keys()
                            - js.keys()
                            - target_type_info.full_type._field_defaults.keys()):  # noqa: W0212
            raise FromJsonConversionError(js, path, target_type_info.full_type,
                                          f"missing keys: {missing_keys}")

        # a type-object for type T can be "called" to construct an instance
        instance_factory = cast("Callable[..., NamedTupleTarget_co]", target_type_info.full_type)
        # NamedTuple._fields is public
        # noinspection PyProtectedMember
        return instance_factory(
            **{field_name: from_json(json_value_or_default(field_name),
                                     target_type_info.annotations.get(field_name, object),
                                     path.append(field_name))
               for field_name in
               target_type_info.full_type._fields}
        )


class FromNamedTuple(ToJsonConverter[NamedTupleSource_contra]):
    """Converts objects of type :class:`typing.NamedTuple`.

    A :class:`typing.NamedTuple` is converted to a ``dict`` with keys corresponding to the
    fields of the ``NamedTuple`` and values being converted with their respective
    :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any) -> bool:
        return isinstance(o, _NamedTupleProtocol)

    def convert(
            self, o: NamedTupleSource_contra, to_json: Callable[[Any], Json]
    ) -> Json:
        # _asdict is actually public
        # noinspection PyProtectedMember
        return {k: to_json(v) for k, v in o._asdict().items()}
