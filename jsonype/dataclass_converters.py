from dataclasses import MISSING, Field, fields, is_dataclass
from typing import Any, Callable, ClassVar, Mapping, Optional, Protocol, TypeVar

from jsonype.base_types import Json
from jsonype.basic_from_json_converters import (ContainedTargetType_co, FromJsonConversionError,
                                                FromJsonConverter, TargetType_co)
from jsonype.basic_to_json_converters import ToJsonConverter


# Only "known" field of a dataclass
class DataClassProtocol(Protocol):   # noqa: R0903
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


DataclassTarget_co = TypeVar("DataclassTarget_co", bound=DataClassProtocol, covariant=True)
DataclassTarget_contra = TypeVar("DataclassTarget_contra",
                                 bound=DataClassProtocol, contravariant=True)


class ToDataclass(FromJsonConverter[DataclassTarget_co, TargetType_co]):
    """Convert an object representing JSON to a :class:`dataclasses.dataclass`.

    The JSON object is expected to have keys corresponding to the fields of the dataclass.
    Each value is converted to the corresponding field type.
    """

    def __init__(self, strict: bool = False) -> None:
        self._strict = strict

    def can_convert(self, target_type: type, _origin_of_generic: Optional[type]) -> bool:
        return is_dataclass(target_type)

    def convert(
            self,
            js: Json,
            target_type: type[DataclassTarget_co],
            annotations: Mapping[str, type],
            from_json: Callable[[Json, type], ContainedTargetType_co]
    ) -> DataclassTarget_co:
        if not isinstance(js, Mapping):
            raise FromJsonConversionError(js, target_type)
        if self._strict and (extra_keys := js.keys() - annotations.keys()):
            raise FromJsonConversionError(js, target_type, f"unexpected keys: {extra_keys}")
        if missing_keys := {
                field.name for field in fields(target_type)
                if field.default == MISSING and field.default_factory == MISSING
        } - js.keys():
            raise FromJsonConversionError(
                js, target_type, f"missing keys: {missing_keys}"
            )
        return target_type(**{
            field_name: from_json(field_value, annotations[field_name])
            for field_name, field_value in js.items()
            if field_name in annotations
        })


class FromDataclass(ToJsonConverter[DataclassTarget_contra]):
    """Converts objects of :class:`dataclasses.dataclass`.

    A dataclass is converted to a ``dict`` with keys corresponding to the
    fields of the dataclass and values being converted with their respective
    :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any) -> bool:
        return is_dataclass(o) and not isinstance(o, type)

    def convert(self, o: DataclassTarget_contra, to_json: Callable[[Any], Json]) -> Json:
        return {field.name: to_json(getattr(o, field.name)) for field in fields(o)}
