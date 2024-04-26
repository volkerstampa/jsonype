from inspect import get_annotations
from random import choice, choices, gauss, randint, randrange, uniform
from string import ascii_letters, digits, printable
from sys import float_info
from types import NoneType
from typing import (Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple, TypeAlias,
                    TypedDict, TypeVar, Union, cast)
from unittest import TestCase, main

from jsont import TypedJson

_T = TypeVar("_T")


ObjectFactory: TypeAlias = Callable[[int, Sequence["ObjectFactory[_T]"]], tuple[_T, type[_T]]]

typed_json = TypedJson()
strict_typed_json = TypedJson(strict=True)


class TypedJsonTestCase(TestCase):

    def test_simple(self) -> None:
        for simple_obj in [0, -1, 2, 0., 1., -2., True, False, "Hello", "", None]:
            self.assert_can_convert_from_to_json(simple_obj, type(simple_obj))

    def test_simple_with_union_type(self) -> None:
        for i in [0, "Hello", None]:
            # Union is a type-special-form so cast to type explicitly
            self.assert_can_convert_from_to_json(
                i, cast(type[Optional[Union[int, str]]], Optional[Union[int, str]]))

    def test_homogeneous_list(self) -> None:
        # just for defining ty as TypeAlias
        # noinspection PyTypeHints,PyUnusedLocal
        ty: TypeAlias = Any
        for li, ty in [
            ([0, -1, 2], int),
            ([0., 1., -2.], float),
            ([True, False], bool),
            (["Hello", ""], str),
            ([None], NoneType)
        ]:
            self.assert_can_convert_from_to_json(li, list[ty])

    def test_untyped_list(self) -> None:
        self.assert_can_convert_from_to_json([1], list)
        self.assert_can_convert_from_to_json(["Hi"], List)

    def test_inhomogeneous_list(self) -> None:
        self.assert_can_convert_from_to_json([1, 0., True, None, "Hello"],
                                             list[Union[int, float, bool, None, str]])

    def test_inhomogeneous_tuple(self) -> None:
        self.assert_can_convert_from_to_json((1, 0., True, None, "Hello"),
                                             tuple[int, float, bool, None, str])

    def test_empty_tuple(self) -> None:
        self.assert_can_convert_from_to_json((), tuple[()])

    def test_homogeneous_mapping(self) -> None:
        # just for defining ty as TypeAlias
        # noinspection PyTypeHints,PyUnusedLocal
        ty: TypeAlias = Any
        for m, ty in [
            ({"k1": 1}, int),
            ({"k1": True, "k2": False}, bool),
            ({"k1": None}, NoneType)
        ]:
            self.assert_can_convert_from_to_json(m, dict[str, ty])

    def test_inhomogeneous_mapping(self) -> None:
        self.assert_can_convert_from_to_json({"k1": 1, "k2": "Demo"}, dict[str, Union[int, str]])

    def test_typed_dict_relaxed(self) -> None:
        class Map(TypedDict):
            k1: float
            k2: int

        inp = {"k1": 1., "k2": 2, "un": "used"}
        expected = {k: v for k, v in inp.items() if k in get_annotations(Map)}
        self.assert_can_convert_from_to_json_relaxed(inp, expected, Map)

    def test_typed_dict(self) -> None:
        class Map(TypedDict):
            k1: float
            k2: int

        self.assert_can_convert_from_to_json({"k1": 1., "k2": 2}, Map)

    def test_random_objects(self) -> None:
        for _ in range(500):
            self.assert_can_convert_from_to_json(*(self._random_typed_object(8)))

    def assert_can_convert_from_to_json(self, obj: Any, ty: type[_T]) -> None:
        try:
            self.assertEqual(
                obj, strict_typed_json.from_json(typed_json.to_json(obj), ty))
        except AssertionError:
            print(f"Cannot convert {obj} to {ty}")  # noqa: T201
            raise

    def assert_can_convert_from_to_json_relaxed(self, inp: Any, expected: Any, ty: type[_T]) \
            -> None:
        try:
            self.assertEqual(
                expected, typed_json.from_json(typed_json.to_json(inp), ty))
        except AssertionError:
            print(f"Cannot convert {inp} to {ty}")  # noqa: T201
            raise

    def _random_typed_object(self, size: int,
                             factories: Optional[Sequence[ObjectFactory[_T]]] = None) \
            -> tuple[_T, type[_T]]:
        factories = factories or self._all_types_factories()
        return choice(factories)(size, factories)

    def _ambiguous_types_factories(self) -> Sequence[ObjectFactory[Any]]:
        return (self._random_tuple,
                self._random_tuple_with_ellipsis,
                self._random_untyped_list,
                self._random_untyped_map)

    def _unambiguous_types_factories(self) -> Sequence[ObjectFactory[Any]]:
        return (self._random_int,
                self._random_float,
                self._random_bool,
                self._none,
                self._random_str,
                self._random_sequence,
                self._random_map,
                self._random_typed_map)

    def _all_types_factories(self) -> Sequence[ObjectFactory[Any]]:
        return tuple(self._ambiguous_types_factories()) + tuple(self._unambiguous_types_factories())

    @staticmethod
    def _random_int(_size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[int, type[int]]:
        return randint(-2 ** 63, 2 ** 63 - 1), int

    @staticmethod
    def _random_float(_size: int, _factories: Sequence[ObjectFactory[Any]]) \
            -> tuple[float, type[float]]:
        f = choices([-float_info.max,
                     uniform(-float_info.max, 0),
                     gauss(0, 10),
                     uniform(0, float_info.max),
                     float_info.max],
                    weights=[1, 3, 5, 3, 1])
        return f[0], float

    @staticmethod
    def _random_bool(_size: int, _factories: Sequence[ObjectFactory[Any]]) \
            -> tuple[bool, type[bool]]:
        return bool(randint(0, 1)), bool

    @staticmethod
    def _none(_size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[None, Any]:
        return None, Any

    @staticmethod
    def _random_str(size: int, _factories: Sequence[ObjectFactory[Any]]) -> tuple[str, type[str]]:
        return "".join(choices(printable, k=randrange(size))), str

    def _random_sequence(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[Sequence[_T], type[Sequence[_T]]]:
        seq, types = self._random_values(size, factories)
        # Union[*types] is not a valid type so cast to a type
        # TypeAliases shall be top-level, but otherwise element_type is not a valid type
        # noinspection PyTypeHints
        element_type: TypeAlias = cast(type, Union[*types] if seq else Any)
        return list(seq), Sequence[element_type]

    def _random_untyped_list(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[Sequence[_T], type[list[Any]]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        seq, _types = self._random_values(size, unambiguous_factories)
        return list(seq), List

    def _random_tuple(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
        seq, types = self._random_values(size, factories)
        # tuple[*var] it interpreted as object, so it needs a cast
        return tuple(seq), cast(type[tuple[_T, ...]], Tuple[*types])

    def _random_tuple_with_ellipsis(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[tuple[_T, ...], type[tuple[_T, ...]]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        seq, types = self._random_values(size, unambiguous_factories)
        # tuple[*var] it interpreted as object, so it needs a cast
        return tuple(seq), cast(type[tuple[_T, ...]],
                                Tuple[*insert_random_ellipsis(types)])

    def _random_map(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[Mapping[str, _T], type[Mapping[str, _T]]]:
        vals, types = self._random_values(size, factories)
        # Union[*types] is not a valid type so cast to a type
        # TypeAliases shall be top-level, but otherwise element_type is not a valid type
        # noinspection PyTypeHints
        value_types: TypeAlias = cast(type, Union[*types] if vals else Any)
        return ({self._random_str(size, factories)[0]: val for val in vals},
                Mapping[str, value_types])

    def _random_untyped_map(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[Mapping[str, _T], type[Mapping[str, Any]]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        vals, _types = self._random_values(size, unambiguous_factories)
        return {self._random_str(size, factories)[0]: val for val in vals}, Mapping

    def _random_typed_map(self, size: int, factories: Sequence[ObjectFactory[Any]]) \
            -> tuple[Mapping[str, Any], type[Mapping[str, Any]]]:
        vals, types = self._random_values(size, factories)
        keys = [self._random_symbol() for _ in vals]
        # https://github.com/python/mypy/issues/7178
        map_type = TypedDict(self._random_symbol(), dict(zip(keys, types)))  # type: ignore[misc] # noqa: UP013
        # the types of vals are in types, and they are zipped in the same way with
        # the keys as the vals are zipped here so this should actually be safe.
        return map_type(**dict(zip(keys, vals))), map_type  # type: ignore[typeddict-item]

    @staticmethod
    def _random_symbol() -> str:
        return "".join(choices(ascii_letters + digits, k=10))

    def _random_values(self, size: int, factories: Sequence[ObjectFactory[_T]]) \
            -> tuple[Sequence[_T], Sequence[type[_T]]]:
        previous_types: list[type[_T]] = []

        def add_to_previous(val: Any, ty: type[_T]) -> tuple[_T, type[_T]]:
            previous_types.append(ty)
            return val, ty

        def cannot_convert(val: _T, ty: type[_T]) -> bool:
            try:
                typed_json.from_json(typed_json.to_json(val), ty)
            except ValueError:
                return True
            return False

        def cannot_convert_to_previous_type(val: _T) -> bool:
            return all(cannot_convert(val, ty) for ty in previous_types)

        values_with_types: Iterable[tuple[_T, type[_T]]] = \
            (self._random_typed_object(size // 2, factories) for _ in range(randrange(size)))
        # zip is an Iterable which has only a single type-parameter (i.e. must be homogeneous)
        # but when some (Any, type) tuples are zipped we do get a ([Any], [type])
        value_and_types = cast(
            tuple[Sequence[_T], Sequence[type[_T]]],
            tuple(zip(*(add_to_previous(val, ty) for val, ty in values_with_types if
                  cannot_convert_to_previous_type(val)))))
        return value_and_types or ((), ())


def insert_random_ellipsis(types: Sequence[type]) -> Sequence[type]:
    if not types:
        return ()
    ellipsis_start = randint(0, len(types) - 1)
    ellipsis_end = randint(ellipsis_start + 1, len(types))
    types_with_ellipsis: list[Any] = list(types)
    types_with_ellipsis[ellipsis_start:ellipsis_end] = [...]
    return types_with_ellipsis


if __name__ == "__main__":
    main()
