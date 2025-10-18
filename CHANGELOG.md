Changelog
=========

## next

- Switch from poetry to uv
- Add test coverage reporting and require 100% in CI

## 0.6.1

- Include marker file py.typed to indicate that package contains type-hints

## 0.6.0

- Add converters for the following Python types that convert from/to str: datetime, time, date, UUID, Path, bytes, 
  SplitResult (URLs).
- Add generic function based converters `FunctionBasedFromSimpleJsonConverter` and `FunctionBasedToSimpleJsonConverter`.
  They allow to write a converter from/to a simple JSON type by just providing a corresponding function.

## 0.5.0

- Add support for custom converters. You can now create a new TypedJson instance from an existing one
  by pre- or appending the list of converts with custom ones.
- Breaking Change: `TypedJson.__init__` takes two lists for from and to json converters. This allows
  to initialize TypedJson with custom converters. There is a convenience factory method `TypedJson.default()` 
  for creating a TypedJson with default converters. 
- Breaking Change: FromJsonConverter.can_convert now also takes the json object to be converted such that
  a converter can also base its decision on the input value and not only on the target type

## 0.4.0

- Include path info in FromJsonConversionError to refer to the part of the JSON document 
  that couldn't be converted.

## 0.3.1

- Add support for converting from/to dataclasses

## 0.2.0

- Add support for converting from/to NamedTuples

## 0.1.0

- Initial release