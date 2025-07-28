"""
Exceptions for CDM MinIO Data Governance API Client
"""

from typing import Optional


class DataGovernanceError(Exception):
    """Base exception for all data governance API errors"""

    pass


class APIError(DataGovernanceError):
    """Raised when the API returns an error response"""

    def __init__(
        self,
        error: Optional[int] = None,
        error_type: Optional[str] = None,
        message: Optional[str] = None,
    ):
        # API ErrorResponse fields only
        self.error = error
        self.error_type = error_type
        self.message = message

        # Use the API message if available, otherwise fallback
        display_message = message or error_type or "Unknown error"
        super().__init__(display_message)
