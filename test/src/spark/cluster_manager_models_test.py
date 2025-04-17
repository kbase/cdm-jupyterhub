"""Tests for the models module."""

from spark import cluster_manager_models

def test_models_imports():
    """Test that models module can be imported."""
    assert cluster_manager_models is not None


def test_noop():
    """Simple placeholder test."""
    assert 1 == 1 