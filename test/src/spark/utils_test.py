import socket
from unittest import mock

import pytest
from pyspark.sql import SparkSession

from spark.utils import get_spark_session, _get_jars, JAR_DIR


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
    with mock.patch.dict('os.environ', {}):
        spark_session = get_spark_session("TestApp", local=True)
        print("Created local Spark session.")
        try:
            yield spark_session
        finally:
            spark_session.stop()
            print("Stopped local Spark session.")


def test_spark_session_local(spark_session_local):
    """Test local Spark session configuration."""
    assert isinstance(spark_session_local, SparkSession)
    assert spark_session_local.conf.get("spark.master") == "local[*]"
    assert spark_session_local.conf.get("spark.app.name") == "TestApp"


def test_get_jars_success():
    jar_names = ["jar1.jar", "jar2.jar"]
    expected = f"{JAR_DIR}/jar1.jar, {JAR_DIR}/jar2.jar"

    with mock.patch('os.path.exists', return_value=True):
        result = _get_jars(jar_names)
        assert result == expected


def test_get_jars_missing_file():
    jar_names = ["jar1.jar", "jar2.jar"]

    def side_effect(path):
        return "jar1.jar" in path

    with mock.patch('os.path.exists', side_effect=side_effect):
        with pytest.raises(FileNotFoundError) as excinfo:
            _get_jars(jar_names)
        assert "Some required jars are not found" in str(excinfo.value)
