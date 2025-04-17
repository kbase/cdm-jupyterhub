import os

import requests

from service.arg_checkers import not_falsy

from .cluster_manager_models import (
    ClusterDeleteResponse,
    ErrorResponse,
    HealthResponse,
    SparkClusterConfig,
    SparkClusterCreateResponse,
    SparkClusterStatus,
)


class SparkClusterManagerClient:
    """Client for the CDM Spark Cluster Manager API."""

    def __init__(self, api_url: str | None = None):
        """
        Initialize the Spark Cluster Manager API client.

        Args:
            api_url: Optional Spark Cluster Manager API URL. If not provided, will try to get from environment variable.
        """
        self.api_url = not_falsy(
            api_url or os.environ.get("SPARK_CLUSTER_MANAGER_API_URL"),
            "SPARK_CLUSTER_MANAGER_API_URL",
        )

        self.auth_token = not_falsy(
            os.environ.get("KBASE_AUTH_TOKEN"), "KBASE_AUTH_TOKEN"
        )

        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def _parse_error_response(self, response: requests.Response) -> ErrorResponse:
        """
        Parse an error response from the Spark Cluster Manager API.
        """
        try:
            error_data = response.json()
            return ErrorResponse(
                error=error_data.get("error") or response.status_code,
                error_type=error_data.get("error_type") or "api_error",
                message=error_data.get("message")
                or f"API request failed with status code: {response.status_code}",
            )
        except Exception:
            return ErrorResponse(
                error=response.status_code,
                error_type="api_error",
                message=f"API request failed with status code: {response.status_code}",
            )

    def health_check(self) -> HealthResponse | ErrorResponse:
        """
        Check the health of the Spark Cluster Manager API.

        Returns:
            HealthResponse on success, or ErrorResponse on failure
        """
        response = requests.get(f"{self.api_url}/health")

        if not response.ok:
            return self._parse_error_response(response)

        return HealthResponse(**response.json())

    def get_cluster_status(self) -> SparkClusterStatus | ErrorResponse:
        """
        Get the status of the user's Spark cluster.

        Returns:
            SparkClusterStatus on success, or ErrorResponse on failure
        """
        response = requests.get(f"{self.api_url}/clusters", headers=self.headers)

        if not response.ok:
            return self._parse_error_response(response)

        return SparkClusterStatus(**response.json())

    def create_cluster(
        self, config: SparkClusterConfig
    ) -> SparkClusterCreateResponse | ErrorResponse:
        """
        Create a new Spark cluster with the given configuration.

        Args:
            config: SparkClusterConfig object with the cluster configuration

        Returns:
            SparkClusterCreateResponse on success, or ErrorResponse on failure
        """
        response = requests.post(
            f"{self.api_url}/clusters",
            headers=self.headers,
            data=config.model_dump_json(),
        )

        if not response.ok:
            return self._parse_error_response(response)

        return SparkClusterCreateResponse(**response.json())

    def delete_cluster(self) -> ClusterDeleteResponse | ErrorResponse:
        """
        Delete the user's Spark cluster.

        Returns:
            ClusterDeleteResponse on success, or ErrorResponse on failure
        """
        response = requests.delete(f"{self.api_url}/clusters", headers=self.headers)

        if not response.ok:
            return self._parse_error_response(response)

        return ClusterDeleteResponse(**response.json())
