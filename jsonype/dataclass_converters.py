from collections.abc import Mapping
from dataclasses import MISSING, Field, fields, is_dataclass
from typing import Any, Callable, ClassVar, Protocol, TypeVar

from jsonype.base_types import Json, JsonPath
from jsonype.basic_from_json_converters import (ContainedTargetType_co, FromJsonConversionError,
                                                FromJsonConverter, ParameterizedTypeInfo,
                                                TargetType_co)
from jsonype.basic_to_json_converters import ToJsonConverter


# Only "known" field of a dataclass
class DataClassProtocol(Protocol):   # pylint: disable=too-few-public-methods
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


DataclassTarget_co = TypeVar("DataclassTarget_co", bound=DataClassProtocol, covariant=True)
DataclassTarget_contra = TypeVar("DataclassTarget_contra",
                                 bound=DataClassProtocol, contravariant=True)


class ToDataclass(FromJsonConverter[DataclassTarget_co, TargetType_co]):
    """Convert an object representing JSON to a :func:`dataclasses.dataclass`.

    The JSON object is expected to have keys corresponding to the fields of the dataclass.
    Each value is converted to the corresponding field type.
    """

    def __init__(self, strict: bool = False) -> None:
        self._strict = strict

    def can_convert(
            self, _js: Json, target_type_info: ParameterizedTypeInfo[Any]
    ) -> bool:
        return is_dataclass(target_type_info.full_type)

    def convert(
            self,
            js: Json,
            target_type_info: ParameterizedTypeInfo[DataclassTarget_co],
            path: JsonPath,
            from_json: Callable[[Json, type, JsonPath], ContainedTargetType_co]
    ) -> DataclassTarget_co:
        if not isinstance(js, Mapping):
            raise FromJsonConversionError(js, path, target_type_info.full_type)
        if self._strict and (extra_keys := js.keys() - target_type_info.annotations.keys()):
            raise FromJsonConversionError(js, path, target_type_info.full_type,
                                          f"unexpected keys: {extra_keys}")
        if missing_keys := {
                field.name for field in fields(target_type_info.full_type)
                if field.default == MISSING and field.default_factory == MISSING
        } - js.keys():
            raise FromJsonConversionError(
                js, path, target_type_info.full_type, f"missing keys: {missing_keys}"
            )
        return target_type_info.full_type(**{
            field_name: from_json(field_value,
                                  target_type_info.annotations[field_name],
                                  path.append(field_name))
            for field_name, field_value in js.items()
            if field_name in target_type_info.annotations
        })


class FromDataclass(ToJsonConverter[DataclassTarget_contra]):
    """Converts objects of :func:`dataclasses.dataclass`.

    A dataclass is converted to a ``dict`` with keys corresponding to the
    fields of the dataclass and values being converted with their respective
    :class:`ToJsonConverter`.
    """

    def can_convert(self, o: Any) -> bool:
        return is_dataclass(o) and not isinstance(o, type)

    def convert(self, o: DataclassTarget_contra, to_json: Callable[[Any], Json]) -> Json:
        return {field.name: to_json(getattr(o, field.name)) for field in fields(o)}
