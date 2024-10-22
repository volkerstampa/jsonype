from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from typing import Literal, Union

JsonNull = Literal[None]
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]


@dataclass(frozen=True)
class JsonPath:
    """Represent the path to an element in a nested JSON structure.

    The string representation of this path follows the ideas of
    `JSONPath <https://goessner.net/articles/JsonPath/>`_ .
    """

    _elements: tuple[str | int, ...] = ()

    def __str__(self) -> str:
        def key_join(elements: Iterable[str]) -> str:
            return "." + ".".join(elements)

        def index_join(elements: Iterable[int]) -> str:
            return "[" + "][".join(map(str, elements)) + "]"

        path = "".join(key_join(elements) if path_type is str  # type: ignore[arg-type]
                       else index_join(elements)  # type: ignore[arg-type]
                       for path_type, elements in groupby(self._elements, type))
        return f"${path}"

    def append(self, e: str | int) -> "JsonPath":
        return JsonPath((*self._elements, e))
