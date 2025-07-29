"""
Modern API client for CDM MinIO Data Governance service
"""

import os
from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

from service.arg_checkers import not_falsy

from .exceptions import APIError
from .models import (
    CredentialsResponse,
    HealthResponse,
    PathAccessInfoResponse,
    PathRequest,
    PublicAccessResponse,
    SharePathRequest,
    SharePathResponse,
    SqlWarehousePrefixResponse,
    UnsharePathRequest,
    UnsharePathResponse,
    UserPoliciesResponse,
    UserWorkspaceResponse,
)


class DataGovernanceClient:

    def __init__(self, kbase_token: Optional[str] = None):
        """
        Initialize the DataGovernanceClient.

        Args:
            kbase_token: KBase authentication token. If None, reads from KBASE_AUTH_TOKEN env var

        Reads configuration from environment variables:
        - CDM_DATA_GOVERNANCE_API_URL: Base URL for the data governance API
        - KBASE_AUTH_TOKEN: KBase authentication token (if kbase_token not provided)
        """
        # Read required environment variables
        self.base_url = str(
            not_falsy(
                os.environ.get("CDM_DATA_GOVERNANCE_API_URL"),
                "CDM_DATA_GOVERNANCE_API_URL",
            )
        )
        self.kbase_token = kbase_token or str(
            not_falsy(os.environ.get("KBASE_AUTH_TOKEN"), "KBASE_AUTH_TOKEN")
        )

        # Internal client (created lazily)
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create the underlying httpx client"""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.kbase_token}",
                "Content-Type": "application/json",
            }

            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(60.0),
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response and raise appropriate exceptions"""
        if 200 <= response.status_code < 300:
            return response.json()
        else:
            # Parse error response following API's ErrorResponse model
            error_code = None
            error_type = None
            error_message = None

            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    # API returns: {"error": int|None, "error_type": str|None, "message": str|None}
                    error_code = error_data.get("error")
                    error_type = error_data.get("error_type")
                    error_message = error_data.get("message")
            except Exception:
                # Fallback for JSON parsing failures
                error_message = response.text or f"HTTP {response.status_code}"

            # Raise exception with API error fields only
            raise APIError(
                error=error_code,
                error_type=error_type,
                message=error_message,
            )

    def _get(self, path: str, response_class: Type[T]) -> T:
        """Helper method for GET requests"""
        response = self._get_client().get(path)
        data = self._handle_response(response)
        return response_class(**data)

    def _post(self, path: str, request_data: BaseModel, response_class: Type[T]) -> T:
        """Helper method for POST requests with request body"""
        response = self._get_client().post(path, json=request_data.model_dump())
        data = self._handle_response(response)
        return response_class(**data)

    def health_check(self) -> HealthResponse:
        """Check service health"""
        return self._get("/health", HealthResponse)

    def get_credentials(self) -> CredentialsResponse:
        """Get user credentials for MinIO access"""
        return self._get("/credentials/", CredentialsResponse)

    def get_workspace(self) -> UserWorkspaceResponse:
        """Get user workspace information"""
        return self._get("/workspaces/me", UserWorkspaceResponse)

    def share_path(self, request: SharePathRequest) -> SharePathResponse:
        """Share a path with users and/or groups"""
        return self._post("/sharing/share", request, SharePathResponse)

    def unshare_path(self, request: UnsharePathRequest) -> UnsharePathResponse:
        """Remove sharing permissions from users and/or groups"""
        return self._post("/sharing/unshare", request, UnsharePathResponse)

    def get_user_policies(self) -> UserPoliciesResponse:
        """Get user policy information"""
        return self._get("/workspaces/me/policies", UserPoliciesResponse)

    def make_public(self, request: PathRequest) -> PublicAccessResponse:
        """Make a path publicly accessible"""
        return self._post("/sharing/make-public", request, PublicAccessResponse)

    def make_private(self, request: PathRequest) -> PublicAccessResponse:
        """Make a path completely private"""
        return self._post("/sharing/make-private", request, PublicAccessResponse)

    def get_path_access_info(self, request: PathRequest) -> PathAccessInfoResponse:
        """Get access information for a specific path"""
        return self._post("/sharing/get_path_access_info", request, PathAccessInfoResponse)

    def get_sql_warehouse_prefix(self) -> SqlWarehousePrefixResponse:
        """Get SQL warehouse prefix for the current user"""
        return self._get("/workspaces/me/sql-warehouse-prefix", SqlWarehousePrefixResponse)
