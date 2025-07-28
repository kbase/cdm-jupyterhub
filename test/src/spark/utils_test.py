"""Tests for the spark.utils module."""

from spark import utils


def test_utils_imports():
    """Test that utils module can be imported."""
    assert utils is not None


def test_noop():
    """Simple placeholder test."""
    assert 1 == 1
