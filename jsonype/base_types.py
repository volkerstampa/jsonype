from collections.abc import Mapping, Sequence
from typing import Literal, Union

JsonNull = Literal[None]
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]
