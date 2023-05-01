from random import choice, choices, gauss, randint, randrange, uniform
from string import ascii_letters, digits, printable
from sys import float_info
from types import NoneType
from typing import (Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple, Type,
                    TypedDict, Union, cast)
from unittest import TestCase, main

from jsont.typed_json import T, TypedJson

ObjectFactory = Callable[[int, Sequence["ObjectFactory"]], Tuple[T, Type[T]]]

typed_json = TypedJson()


class TypedJsonTestCase(TestCase):

    def test_simple(self):
        for simple_obj in [0, -1, 2, 0., 1., -2., True, False, "Hello", "", None]:
            self.assert_can_convert_from_to_json(simple_obj, type(simple_obj))

    def test_simple_with_union_type(self):
        for i in [0, "Hello", None]:
            self.assert_can_convert_from_to_json(i, Optional[Union[int, str]])

    def test_homogeneous_sequence(self):
        for li, ty in [
            ([0, -1, 2], int),
            ([0., 1., -2.], float),
            ([True, False], bool),
            (["Hello", ""], str),
            ([None], NoneType)
        ]:
            self.assert_can_convert_from_to_json(li, Sequence[ty])

    def test_inhomogeneous_sequence(self):
        self.assert_can_convert_from_to_json([1, 0., True, None, "Hello"],
                                             Sequence[Union[int, float, bool, None, str]])

    def test_homogeneous_mapping(self):
        for m, ty in [
            ({"k1": 1}, int),
            ({"k1": True, "k2": False}, bool),
            ({"k1": None}, NoneType)
        ]:
            self.assert_can_convert_from_to_json(m, Mapping[str, ty])

    def test_inhomogeneous_mapping(self):
        self.assert_can_convert_from_to_json({"k1": 1, "k2": "Demo"}, Mapping[str, Union[int, str]])

    def test_typed_dict(self) -> None:
        class Map(TypedDict):
            k1: float
            k2: int

        self.assert_can_convert_from_to_json({"k1": 1., "k2": 2}, Map)

    def test_random_objects(self):
        for _ in range(500):
            self.assert_can_convert_from_to_json(*(self._random_typed_object(8)))

    def assert_can_convert_from_to_json(self, obj: Any, ty: Type[T]):
        try:
            self.assertEqual(
                obj, typed_json.from_json(typed_json.to_json(obj), ty))
        except AssertionError:
            print(f"Cannot convert {obj} to {ty}")
            raise

    def _random_typed_object(self, size: int,
                             factories: Optional[Sequence[ObjectFactory]] = None) \
            -> Tuple[T, Type[T]]:
        factories = factories or self._all_types_factories()
        return choice(factories)(size, factories)

    def _ambiguous_types_factories(self) -> Sequence[ObjectFactory]:
        return (self._random_tuple,
                self._random_tuple_with_ellipsis,
                self._random_untyped_sequence,
                self._random_untyped_map)

    def _unambiguous_types_factories(self) -> Sequence[ObjectFactory]:
        return (self._random_int,
                self._random_float,
                self._random_bool,
                self._none,
                self._random_str,
                self._random_sequence,
                self._random_map,
                self._random_typed_map)

    def _all_types_factories(self) -> Sequence[ObjectFactory]:
        return tuple(self._ambiguous_types_factories()) + tuple(self._unambiguous_types_factories())

    @staticmethod
    def _random_int(_size: int, _factories: Sequence[ObjectFactory]) -> Tuple[int, Type[int]]:
        return randint(-2 ** 63, 2 ** 63 - 1), int

    @staticmethod
    def _random_float(_size: int, _factories: Sequence[ObjectFactory]) -> Tuple[float, Type[float]]:
        f = choices([-float_info.max,
                     uniform(-float_info.max, 0),
                     gauss(0, 10),
                     uniform(0, float_info.max),
                     float_info.max],
                    weights=[1, 3, 5, 3, 1])
        return f[0], float

    @staticmethod
    def _random_bool(_size: int, _factories: Sequence[ObjectFactory]) -> Tuple[bool, Type[bool]]:
        return bool(randint(0, 1)), bool

    @staticmethod
    def _none(_size: int, _factories: Sequence[ObjectFactory]) -> Tuple[None, Any]:
        return None, Any

    @staticmethod
    def _random_str(size: int, _factories: Sequence[ObjectFactory]) -> Tuple[str, Type[str]]:
        return ''.join(choices(printable, k=randrange(size))), str

    def _random_sequence(self, size: int, factories: Sequence[ObjectFactory]) \
            -> Tuple[Sequence[T], Type[Sequence[T]]]:
        seq, types = self._random_values(size, factories)
        return list(seq), Sequence[Union[*types]]  # type: ignore

    def _random_untyped_sequence(self, size: int, factories: Sequence[ObjectFactory]) \
            -> Tuple[Sequence[T], Type[Sequence]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        seq, _types = self._random_values(size, unambiguous_factories)
        return list(seq), Sequence

    def _random_tuple(self, size, factories: Sequence[ObjectFactory]) \
            -> Tuple[Tuple[Any, ...], Type[Tuple[Any, ...]]]:
        seq, types = self._random_values(size, factories)
        return tuple(seq), cast(Type[Tuple[Any, ...]], Tuple[*types] if seq else Tuple[()])

    def _random_tuple_with_ellipsis(self, size, factories: Sequence[ObjectFactory]) \
            -> Tuple[Tuple[Any, ...], Type[Tuple[Any, ...]]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        seq, types = self._random_values(size, unambiguous_factories)
        return tuple(seq), cast(Type[Tuple[Any, ...]],
                                Tuple[*insert_random_ellipsis(types)] if seq else Tuple[()])

    def _random_map(self, size: int, factories: Sequence[ObjectFactory]) \
            -> Tuple[Mapping[str, T], Type[Mapping[str, T]]]:
        vals, types = self._random_values(size, factories)
        return ({self._random_str(size, factories)[0]: val for val in vals},
                cast(Type[Mapping[str, T]], Mapping[str, Union[*types]]))  # type: ignore

    def _random_untyped_map(self, size: int, factories: Sequence[ObjectFactory]) \
            -> Tuple[Mapping[str, T], Type[Mapping]]:
        unambiguous_factories = tuple(
            frozenset(self._unambiguous_types_factories()).intersection(frozenset(factories)))
        vals, _types = self._random_values(size, unambiguous_factories)
        return {self._random_str(size, factories)[0]: val for val in vals}, Mapping

    def _random_typed_map(self, size: int, factories: Sequence[ObjectFactory]) \
            -> Tuple[Mapping, Type[Mapping]]:
        vals, types = self._random_values(size, factories)
        keys = [self._random_symbol() for _ in vals]
        # noinspection PyPep8Naming
        MapType = TypedDict(self._random_symbol(), dict(zip(keys, types)))  # type: ignore
        return MapType(**dict(zip(keys, vals))), MapType  # type: ignore

    @staticmethod
    def _random_symbol() -> str:
        return ''.join(choices(ascii_letters + digits, k=10))

    def _random_values(self, size, factories: Sequence[ObjectFactory]) \
            -> Tuple[Sequence[Any], Sequence[Type[Any]]]:
        previous_types: List[type] = []

        def add_to_previous(val: Any, ty: Type[Any]) -> Tuple[Any, Type[Any]]:
            previous_types.append(ty)
            return val, ty

        def cannot_convert(val: Any, ty: type) -> bool:
            try:
                typed_json.from_json(typed_json.to_json(val), ty)  # type: ignore
                return False
            except ValueError:
                return True

        def cannot_convert_to_previous_type(val: Any) -> bool:
            return all(cannot_convert(val, ty) for ty in previous_types)

        values_with_types: Iterable[Tuple[Any, Type[Any]]] = \
            (self._random_typed_object(size // 2, factories) for _ in range(randrange(size)))
        value_and_types = cast(Tuple[Sequence[Any], Sequence[Type[Any]]], tuple(
            zip(*(add_to_previous(val, ty) for val, ty in values_with_types if
                  cannot_convert_to_previous_type(val)))))
        return value_and_types or ((), (Any,))


def insert_random_ellipsis(types: Sequence[type]) -> Sequence[Any]:
    ellipsis_start = randint(0, len(types) - 1)
    ellipsis_end = randint(ellipsis_start + 1, len(types))
    types_with_ellipsis: List[Any] = list(types)
    types_with_ellipsis[ellipsis_start:ellipsis_end] = [...]
    return types_with_ellipsis


if __name__ == '__main__':
    main()
