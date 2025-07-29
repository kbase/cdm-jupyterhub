"""
Modern API client for CDM MinIO Data Governance service
"""

import os
from typing import Any, Optional

import httpx

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

    def health_check(self) -> HealthResponse:
        """Check service health"""
        response = self._get_client().get("/health")
        data = self._handle_response(response)
        return HealthResponse(**data)

    def get_credentials(self) -> CredentialsResponse:
        """Get user credentials for MinIO access"""
        response = self._get_client().get("/credentials/")
        data = self._handle_response(response)
        return CredentialsResponse(**data)

    def get_workspace(self) -> UserWorkspaceResponse:
        """Get user workspace information"""
        response = self._get_client().get("/workspaces/me")
        data = self._handle_response(response)
        return UserWorkspaceResponse(**data)

    def share_path(self, request: SharePathRequest) -> SharePathResponse:
        """Share a path with users and/or groups"""
        response = self._get_client().post(
            "/sharing/share", json=request.model_dump()
        )
        data = self._handle_response(response)
        return SharePathResponse(**data)

    def unshare_path(self, request: UnsharePathRequest) -> UnsharePathResponse:
        """Remove sharing permissions from users and/or groups"""
        response = self._get_client().post(
            "/sharing/unshare", json=request.model_dump()
        )
        data = self._handle_response(response)
        return UnsharePathResponse(**data)

    def get_user_policies(self) -> UserPoliciesResponse:
        """Get user policy information"""
        response = self._get_client().get("/workspaces/me/policies")
        data = self._handle_response(response)
        return UserPoliciesResponse(**data)

    def make_public(self, request: PathRequest) -> PublicAccessResponse:
        """Make a path publicly accessible"""
        response = self._get_client().post(
            "/sharing/make-public", json=request.model_dump()
        )
        data = self._handle_response(response)
        return PublicAccessResponse(**data)

    def make_private(self, request: PathRequest) -> PublicAccessResponse:
        """Make a path completely private"""
        response = self._get_client().post(
            "/sharing/make-private", json=request.model_dump()
        )
        data = self._handle_response(response)
        return PublicAccessResponse(**data)

    def get_path_access_info(self, request: PathRequest) -> PathAccessInfoResponse:
        """Get access information for a specific path"""
        response = self._get_client().post(
            "/sharing/get_path_access_info", json=request.model_dump()
        )
        data = self._handle_response(response)
        return PathAccessInfoResponse(**data)

    def get_sql_warehouse_prefix(self) -> SqlWarehousePrefixResponse:
        """Get SQL warehouse prefix for the current user"""
        response = self._get_client().get("/workspaces/me/sql-warehouse-prefix")
        data = self._handle_response(response)
        return SqlWarehousePrefixResponse(**data)
