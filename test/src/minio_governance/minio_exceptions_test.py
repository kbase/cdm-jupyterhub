"""Tests for the minio_governance.exceptions module."""

from minio_governance import exceptions


def test_exceptions_imports():
    """Test that exceptions module can be imported."""
    assert exceptions is not None


def test_noop():
    """Simple placeholder test."""
    assert 1 == 1 