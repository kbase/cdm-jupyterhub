"""
Modern API client for CDM MinIO Data Governance service
"""

import os
from typing import Any, Optional

import httpx

from service.arg_checkers import not_falsy

from .exceptions import APIError


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
