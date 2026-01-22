"""Tests for string utilities."""
import pytest
from strings import (
    reverse, is_palindrome, capitalize_words, count_vowels,
    truncate, snake_to_camel, camel_to_snake, remove_duplicates
)


def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse("a") == "a"


def test_is_palindrome():
    assert is_palindrome("radar") == True
    assert is_palindrome("hello") == False
    assert is_palindrome("A man a plan a canal Panama") == True


def test_capitalize_words():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("HELLO") == "Hello"


def test_count_vowels():
    assert count_vowels("hello") == 2
    assert count_vowels("xyz") == 0
    assert count_vowels("AEIOU") == 5


def test_truncate():
    assert truncate("hello world", 8) == "hello..."
    assert truncate("hi", 10) == "hi"
    assert truncate("testing", 7) == "testing"


def test_snake_to_camel():
    assert snake_to_camel("hello_world") == "helloWorld"
    assert snake_to_camel("my_var_name") == "myVarName"
    assert snake_to_camel("single") == "single"


def test_camel_to_snake():
    assert camel_to_snake("helloWorld") == "hello_world"
    assert camel_to_snake("myVarName") == "my_var_name"


def test_remove_duplicates():
    assert remove_duplicates("hello") == "helo"
    assert remove_duplicates("aabbcc") == "abc"
