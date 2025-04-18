"""Tests for the cdm_spark_cluster_manager_api_client module.
This model is auto-generated by [openapi-python-client](https://pypi.org/project/openapi-python-client/).
"""

from spark.cdm_spark_cluster_manager_api_client.client import (
    AuthenticatedClient,
    Client,
)


def test_client_imports():
    """Test that client module can be imported."""
    assert Client is not None
    assert AuthenticatedClient is not None


def test_noop():
    """Simple placeholder test."""
    assert 1 == 1
