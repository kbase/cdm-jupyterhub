import socket
from unittest.mock import patch

import pytest
from pyspark.sql import SparkSession

from src.spark.utils import get_spark_session


@pytest.fixture(scope="session")
def mock_spark_master():
    """Create a mock Spark master on an available port."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 0))  # Bind to an available port
    port = server_socket.getsockname()[1]
    server_socket.listen(1)

    print(f"Mock Spark master running on port: {port}")

    yield port

    server_socket.close()
    print("Mock Spark master closed.")


@pytest.fixture
def spark_session_local():
    """Provide a local Spark session for testing."""
    with patch.dict('os.environ', {}):
        spark_session = get_spark_session("TestApp", local=True)
        print("Created local Spark session.")
        try:
            yield spark_session
        finally:
            spark_session.stop()
            print("Stopped local Spark session.")


@pytest.fixture
def spark_session_non_local(mock_spark_master):
    """Provide a non-local Spark session for testing."""
    port = mock_spark_master
    spark_master_url = f"spark://localhost:{port}"
    print(f"Using Spark master URL: {spark_master_url}")

    with patch.dict('os.environ', {"SPARK_MASTER_URL": spark_master_url}):
        spark_session = get_spark_session("TestApp", local=False)
        print("Created non-local Spark session.")
        try:
            yield spark_session, port
        finally:
            spark_session.stop()
            print("Stopped non-local Spark session.")


def test_spark_session_local(spark_session_local):
    """Test local Spark session configuration."""
    assert isinstance(spark_session_local, SparkSession)
    assert spark_session_local.conf.get("spark.master") == "local[*]"
    assert spark_session_local.conf.get("spark.app.name") == "TestApp"


def test_spark_session_non_local(spark_session_non_local):
    """Test non-local Spark session configuration."""
    spark_session, port = spark_session_non_local
    assert isinstance(spark_session, SparkSession)
    assert spark_session.conf.get("spark.master") == f"spark://localhost:{port}"
    assert spark_session.conf.get("spark.app.name") == "TestApp"
