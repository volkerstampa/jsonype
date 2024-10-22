from jsonype import JsonPath


def test_json_path_str_with_empty_path() -> None:
    assert str(JsonPath()) == "$"


def test_json_path_str_with_object_and_array() -> None:
    assert str(JsonPath(("key1", 5, 2, "key2", "key3"))) == "$.key1[5][2].key2.key3"


def test_json_path_str_with_pure_array() -> None:
    assert str(JsonPath((5, 2))) == "$[5][2]"
