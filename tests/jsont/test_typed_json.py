from unittest import TestCase, main

from jsont.typed_json import TypedJson


class TypedJsonTestCase(TestCase):
    def test_simple(self):
        typed_json = TypedJson()
        for simple_obj in [0, -1, 2, 0., 1., -2., True, False, "Hello", "", None]:
            self.assertEqual(simple_obj, typed_json.from_json(typed_json.to_json(simple_obj), type(simple_obj)))


if __name__ == '__main__':
    main()
