"""
Utility functions for CDM MinIO Data Governance integration
"""

import logging
import os
from typing import List, Optional

from service.arg_checkers import not_falsy

from .client import DataGovernanceClient
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

# =============================================================================
# CONSTANTS
# =============================================================================

# TODO: get these from the data governance service
SQL_WAREHOUSE_BUCKET = "cdm-lake"
SQL_USER_WAREHOUSE_PATH = "users-sql-warehouse"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _get_governance_client() -> DataGovernanceClient:
    """
    Get a DataGovernanceClient instance using KBASE_AUTH_TOKEN env var.

    Returns:
        DataGovernanceClient instance
    """
    kbase_token = not_falsy(os.environ.get("KBASE_AUTH_TOKEN"), "KBASE_AUTH_TOKEN")
    return DataGovernanceClient(kbase_token=kbase_token)


def _build_table_path(username: str, namespace: str, table_name: str) -> str:
    """
    Build S3 path for a SQL warehouse table.

    Args:
        username: User's username
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name

    Returns:
        Full S3 path to the table
    """
    # Ensure namespace ends with .db
    if not namespace.endswith(".db"):
        namespace = f"{namespace}.db"

    return f"s3a://{SQL_WAREHOUSE_BUCKET}/{SQL_USER_WAREHOUSE_PATH}/{username}/{namespace}/{table_name}"


def check_governance_health() -> HealthResponse:
    """
    Check data governance service health.

    Returns:
        HealthResponse with service status
    """
    client = _get_governance_client()
    return client.health_check()


def get_minio_credentials() -> CredentialsResponse:
    """
    Get MinIO credentials for the current user and set them as environment variables.

    Sets the following environment variables:
    - MINIO_ACCESS_KEY: User's MinIO access key
    - MINIO_SECRET_KEY: User's MinIO secret key

    Returns:
        CredentialsResponse with username, access_key, and secret_key
    """
    client = _get_governance_client()
    credentials = client.get_credentials()

    # Set MinIO credentials as environment variables
    if os.environ.get("USE_DATA_GOVERNANCE_CREDENTIALS", "false") == "true":
        os.environ["MINIO_ACCESS_KEY"] = credentials.access_key
        os.environ["MINIO_SECRET_KEY"] = credentials.secret_key
    else:
        credentials.access_key = str(os.environ.get("MINIO_ACCESS_KEY"))
        credentials.secret_key = str(os.environ.get("MINIO_SECRET_KEY"))

    return credentials


def get_my_sql_warehouse() -> SqlWarehousePrefixResponse:
    """
    Get SQL warehouse prefix for the current user.

    Returns:
        SqlWarehousePrefixResponse with username and sql_warehouse_prefix
    """
    client = _get_governance_client()
    return client.get_sql_warehouse_prefix()


def get_my_workspace() -> UserWorkspaceResponse:
    """
    Get comprehensive workspace information for the current user.

    Returns:
        UserWorkspaceResponse with username, home_paths, groups, policies, and accessible_paths
    """
    client = _get_governance_client()
    return client.get_workspace()


def get_my_policies() -> UserPoliciesResponse:
    """
    Get detailed policy information for the current user.

    Returns:
        UserPoliciesResponse with user_home_policy, user_system_policy, and group_policies
    """
    client = _get_governance_client()
    return client.get_user_policies()



def get_table_access_info(namespace: str, table_name: str) -> PathAccessInfoResponse:
    """
    Get access information for a SQL warehouse table.

    Args:
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name (e.g., "test_employees")
    """
    client = _get_governance_client()
    username = str(not_falsy(os.environ.get("JUPYTERHUB_USER"), "JUPYTERHUB_USER"))

    table_path = _build_table_path(username, namespace, table_name)
    request = PathRequest(path=table_path)
    return client.get_path_access_info(request)


# =============================================================================
# TABLE-SPECIFIC FUNCTIONS - For SQL Warehouse tables
# =============================================================================


def share_table(
    namespace: str,
    table_name: str,
    with_users: Optional[List[str]] = None,
    with_groups: Optional[List[str]] = None,
) -> SharePathResponse:
    """
    Share a SQL warehouse table with users and/or groups.

    Args:
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name (e.g., "test_employees")
        with_users: List of usernames to share with
        with_groups: List of group names to share with

    Returns:
        SharePathResponse with sharing details and success/error information

    Example:
        share_table("analytics", "user_metrics", with_users=["alice", "bob"])
    """
    client = _get_governance_client()
    # Get current user's username from environment variable
    username = str(not_falsy(os.environ.get("JUPYTERHUB_USER"), "JUPYTERHUB_USER"))

    table_path = _build_table_path(username, namespace, table_name)
    request = SharePathRequest(
        path=table_path, with_users=with_users or [], with_groups=with_groups or []
    )
    response = client.share_path(request)

    # Log warnings if there were errors
    if response.errors:
        logger = logging.getLogger(__name__)
        for error in response.errors:
            logger.warning(f"Error sharing table {namespace}.{table_name}: {error}")

    return response


def unshare_table(
    namespace: str,
    table_name: str,
    from_users: Optional[List[str]] = None,
    from_groups: Optional[List[str]] = None,
) -> UnsharePathResponse:
    """
    Remove sharing permissions from a SQL warehouse table.

    Args:
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name (e.g., "test_employees")
        from_users: List of usernames to remove access from
        from_groups: List of group names to remove access from

    Returns:
        UnsharePathResponse with unsharing details and success/error information

    Example:
        unshare_table("analytics", "user_metrics", from_users=["alice"])
    """
    client = _get_governance_client()
    # Get current user's username from environment variable
    username = str(not_falsy(os.environ.get("JUPYTERHUB_USER"), "JUPYTERHUB_USER"))

    table_path = _build_table_path(username, namespace, table_name)
    request = UnsharePathRequest(
        path=table_path, from_users=from_users or [], from_groups=from_groups or []
    )
    response = client.unshare_path(request)

    # Log warnings if there were errors
    if response.errors:
        logger = logging.getLogger(__name__)
        for error in response.errors:
            logger.warning(f"Error unsharing table {namespace}.{table_name}: {error}")

    return response


def make_table_public(
    namespace: str,
    table_name: str,
) -> PublicAccessResponse:
    """
    Make a SQL warehouse table publicly accessible.

    Args:
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name (e.g., "test_employees")

    Returns:
        PublicAccessResponse with path and is_public status

    Example:
        make_table_public("research", "public_dataset")
    """
    client = _get_governance_client()
    # Get current user's username from environment variable
    username = str(not_falsy(os.environ.get("JUPYTERHUB_USER"), "JUPYTERHUB_USER"))

    table_path = _build_table_path(username, namespace, table_name)
    request = PathRequest(path=table_path)
    return client.make_public(request)


def make_table_private(
    namespace: str,
    table_name: str,
) -> PublicAccessResponse:
    """
    Remove public access from a SQL warehouse table.

    Args:
        namespace: Database namespace (e.g., "test" or "test.db")
        table_name: Table name (e.g., "test_employees")

    Returns:
        PublicAccessResponse with path and is_public status (should be False)

    Example:
        make_table_private("research", "sensitive_data")
    """
    client = _get_governance_client()
    # Get current user's username from environment variable
    username = str(not_falsy(os.environ.get("JUPYTERHUB_USER"), "JUPYTERHUB_USER"))

    table_path = _build_table_path(username, namespace, table_name)
    request = PathRequest(path=table_path)
    return client.make_private(request)
