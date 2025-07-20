"""Tests for utility functions."""

from myequal_ai_common.utils import hello_name, hello_world


def test_hello_world() -> None:
    """Test hello_world function."""
    result = hello_world()
    assert result == "Hello World from MyEqual AI Common Library!"
    assert isinstance(result, str)


def test_hello_name() -> None:
    """Test hello_name function."""
    result = hello_name("Test User")
    assert result == "Hello Test User from MyEqual AI Common Library!"
    assert isinstance(result, str)

    # Test with empty string
    result_empty = hello_name("")
    assert result_empty == "Hello  from MyEqual AI Common Library!"
