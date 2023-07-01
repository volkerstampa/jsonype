from typing import Literal, Mapping, Sequence, Union

JsonNull = Literal[None]
JsonSimple = Union[int, float, str, bool]
JsonComplex = Union[Sequence["Json"], Mapping[str, "Json"]]
Json = Union[JsonNull, JsonSimple, JsonComplex]
