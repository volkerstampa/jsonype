Changelog
=========

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