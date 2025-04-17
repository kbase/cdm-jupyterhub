import os
from typing import Any, Dict, Type, TypeVar

import requests
from pydantic import BaseModel

from service.arg_checkers import not_falsy

from .cluster_manager_models import (
    ClusterDeleteResponse,
    ErrorResponse,
    HealthResponse,
    SparkClusterConfig,
    SparkClusterCreateResponse,
    SparkClusterStatus,
)

T = TypeVar("T", bound=BaseModel)


class SparkClusterManagerClient:
    """Client for the CDM Spark Cluster Manager API."""

    def __init__(self, api_url: str | None = None, auth_token: str | None = None):
        """
        Initialize the Spark Cluster Manager API client.

        Args:
            api_url: Optional Spark Cluster Manager API URL. If not provided, will try to get from environment variable.
            auth_token: Optional auth token. If not provided, will try to get from environment variable.
        """
        self.api_url = not_falsy(
            api_url or os.environ.get("SPARK_CLUSTER_MANAGER_API_URL"),
            "SPARK_CLUSTER_MANAGER_API_URL",
        )

        self.auth_token = not_falsy(
            auth_token or os.environ.get("KBASE_AUTH_TOKEN"), "KBASE_AUTH_TOKEN"
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

    def _request(
        self,
        method: str,
        endpoint: str,
        model_class: Type[T],
        json_data: Dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> T | ErrorResponse:
        """
        Make a request to the API.

        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            model_class: Pydantic model class to parse response into
            json_data: Optional JSON data to send with request
            auth_required: Whether to include authentication headers

        Returns:
            Parsed response model on success, or ErrorResponse on failure
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = (
            self.headers if auth_required else {"Content-Type": "application/json"}
        )

        response = requests.request(
            method=method, url=url, headers=headers, json=json_data
        )

        if not response.ok:
            return self._parse_error_response(response)

        try:
            return model_class(**response.json())
        except Exception as e:
            return ErrorResponse(
                error=None,
                error_type="client_error",
                message=f"Failed to parse response: {str(e)}",
            )

    def health_check(self) -> HealthResponse | ErrorResponse:
        """
        Check the health of the Spark Cluster Manager API.

        Returns:
            HealthResponse on success, or ErrorResponse on failure
        """
        return self._request(
            method="GET",
            endpoint="/health",
            model_class=HealthResponse,
            auth_required=False,
        )

    def get_cluster_status(self) -> SparkClusterStatus | ErrorResponse:
        """
        Get the status of the current authenticated user's Spark cluster.

        Returns:
            SparkClusterStatus on success, or ErrorResponse on failure
        """
        return self._request(
            method="GET", endpoint="/clusters", model_class=SparkClusterStatus
        )

    def create_cluster(
        self, config: SparkClusterConfig
    ) -> SparkClusterCreateResponse | ErrorResponse:
        """
        Create a new Spark cluster with the given configuration for the current authenticated user.

        Args:
            config: SparkClusterConfig object with the cluster configuration

        Returns:
            SparkClusterCreateResponse on success, or ErrorResponse on failure
        """
        return self._request(
            method="POST",
            endpoint="/clusters",
            model_class=SparkClusterCreateResponse,
            json_data=config.model_dump(),
        )

    def delete_cluster(self) -> ClusterDeleteResponse | ErrorResponse:
        """
        Delete the current authenticated user's Spark cluster.

        Returns:
            ClusterDeleteResponse on success, or ErrorResponse on failure
        """
        return self._request(
            method="DELETE", endpoint="/clusters", model_class=ClusterDeleteResponse
        )
