"""
CDM Spark Cluster Manager API Client Wrapper
"""

import os

from service.arg_checkers import not_falsy

from .cdm_spark_cluster_manager_api_client.api.clusters import (
    create_cluster_clusters_post,
    delete_cluster_clusters_delete,
    get_cluster_status_clusters_get,
)
from .cdm_spark_cluster_manager_api_client.api.health import health_check_health_get
from .cdm_spark_cluster_manager_api_client.client import AuthenticatedClient, Client
from .cdm_spark_cluster_manager_api_client.models.cluster_delete_response import (
    ClusterDeleteResponse,
)
from .cdm_spark_cluster_manager_api_client.models.health_response import HealthResponse
from .cdm_spark_cluster_manager_api_client.models.spark_cluster_config import (
    SparkClusterConfig,
)
from .cdm_spark_cluster_manager_api_client.models.spark_cluster_create_response import (
    SparkClusterCreateResponse,
)
from .cdm_spark_cluster_manager_api_client.models.spark_cluster_status import (
    SparkClusterStatus,
)
from .cdm_spark_cluster_manager_api_client.types import Response

DEFAULT_WORKER_COUNT = int(os.environ.get("DEFAULT_WORKER_COUNT", 2))
DEFAULT_WORKER_CORES = int(os.environ.get("DEFAULT_WORKER_CORES", 1))
DEFAULT_WORKER_MEMORY = os.environ.get("DEFAULT_WORKER_MEMORY", "10GiB")
DEFAULT_MASTER_CORES = int(os.environ.get("DEFAULT_MASTER_CORES", 1))
DEFAULT_MASTER_MEMORY = os.environ.get("DEFAULT_MASTER_MEMORY", "10GiB")


def _get_client() -> Client:
    """
    Get an unauthenticated client for the Spark Cluster Manager API.
    """
    api_url = not_falsy(
        os.environ.get("SPARK_CLUSTER_MANAGER_API_URL"), "SPARK_CLUSTER_MANAGER_API_URL"
    )
    return Client(base_url=str(api_url))


def _get_authenticated_client(
    kbase_auth_token: str | None = None,
) -> AuthenticatedClient:
    """
    Get an authenticated client for the Spark Cluster Manager API.
    """
    api_url = not_falsy(
        os.environ.get("SPARK_CLUSTER_MANAGER_API_URL"), "SPARK_CLUSTER_MANAGER_API_URL"
    )
    auth_token = not_falsy(
        os.environ.get("KBASE_AUTH_TOKEN", kbase_auth_token), "KBASE_AUTH_TOKEN"
    )
    return AuthenticatedClient(base_url=str(api_url), token=str(auth_token))


def _raise_api_error(response: Response) -> None:
    """
    Process the API error response and raise an error.
    """
    error_message = f"API Error (HTTP {response.status_code})"

    if hasattr(response, "content") and response.content:
        error_message += f": {response.content}"

    raise ValueError(error_message)


def check_api_health() -> HealthResponse | None:
    """
    Check if the Spark Cluster Manager API is healthy.
    """

    client = _get_client()
    with client as client:
        response: Response[HealthResponse] = health_check_health_get.sync_detailed(
            client=client
        )

    if response.status_code == 200 and response.parsed:
        return response.parsed

    _raise_api_error(response)


def get_cluster_status(
    kbase_auth_token: str | None = None,
) -> SparkClusterStatus | None:
    """
    Get the status of the user's Spark cluster.
    """
    client = _get_authenticated_client(kbase_auth_token)
    with client as client:
        response: Response[SparkClusterStatus] = (
            get_cluster_status_clusters_get.sync_detailed(client=client)
        )

    if response.status_code == 200 and response.parsed:
        # TODO - Parse the response and return information more useful to the user
        return response.parsed

    _raise_api_error(response)


def create_cluster(
    kbase_auth_token: str | None = None,
    worker_count: int = DEFAULT_WORKER_COUNT,
    worker_cores: int = DEFAULT_WORKER_CORES,
    worker_memory: str = DEFAULT_WORKER_MEMORY,
    master_cores: int = DEFAULT_MASTER_CORES,
    master_memory: str = DEFAULT_MASTER_MEMORY,
    force: bool = False,
) -> SparkClusterCreateResponse | None:
    """
    Create a new Spark cluster with the given configuration.

    Args:
        worker_count: Number of worker nodes
        worker_cores: CPU cores per worker
        worker_memory: Memory per worker (e.g., "10GiB")
        master_cores: CPU cores for master
        master_memory: Memory for master (e.g., "10GiB")
        force: Skip confirmation prompt if True
    """

    if not force:
        print(
            "WARNING: Creating a new Spark cluster will terminate your existing cluster."
        )
        print("All active Spark sessions and computations will be lost.")
        # TODO: check existence of user's cluster - by default, upon pod creation, the user's cluster should be created.
        confirmation = input("Do you want to proceed? [y/N]: ").strip().lower() or "N"
        if confirmation not in ("y", "yes"):
            print("Cluster creation aborted.")
            return None

    client = _get_authenticated_client(kbase_auth_token)
    with client as client:
        # Create the config object
        config = SparkClusterConfig(
            worker_count=worker_count,
            worker_cores=worker_cores,
            worker_memory=worker_memory,
            master_cores=master_cores,
            master_memory=master_memory,
        )

        response: Response[SparkClusterCreateResponse] = (
            create_cluster_clusters_post.sync_detailed(client=client, body=config)
        )

    if response.status_code == 201 and response.parsed:
        print(f"Spark cluster created successfully.")
        print(f"Master URL: {response.parsed.master_url}")
        # Set the master URL for the user
        os.environ["SPARK_MASTER_URL"] = response.parsed.master_url
        return response.parsed

    _raise_api_error(response)


def delete_cluster(kbase_auth_token: str | None = None) -> ClusterDeleteResponse | None:
    """
    Delete the user's Spark cluster.
    """
    client = _get_authenticated_client(kbase_auth_token)
    with client as client:
        response: Response[ClusterDeleteResponse] = (
            delete_cluster_clusters_delete.sync_detailed(client=client)
        )

    if response.status_code == 200 and response.parsed:
        print(f"Spark cluster deleted: {response.parsed.message}")
        # Remove the environment variable if it exists
        os.environ.pop("SPARK_MASTER_URL", None)
        return response.parsed

    _raise_api_error(response)
