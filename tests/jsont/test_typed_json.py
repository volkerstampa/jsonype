from typing import Union, Any, Type, Optional
from unittest import TestCase, main

from jsont.typed_json import TypedJson, T


class TypedJsonTestCase(TestCase):

    typed_json = TypedJson()

    def test_simple(self):
        for simple_obj in [0, -1, 2, 0., 1., -2., True, False, "Hello", "", None]:
            self.assert_can_convert_from_to_json(simple_obj, type(simple_obj))

    def test_simple_with_union_type(self):
        for i in [0, "Hello", None]:
            self.assert_can_convert_from_to_json(i, Optional[Union[int, str]])

    def assert_can_convert_from_to_json(self, simple_obj: Any, ty: Type[T]):
        self.assertEqual(
            simple_obj, self.typed_json.from_json(self.typed_json.to_json(simple_obj), ty))




if __name__ == '__main__':
    main()
