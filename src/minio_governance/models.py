"""
Pydantic models for CDM MinIO Data Governance API responses

These models are for internal system use within CDM JupyterHub components.
End users should use functions in minio_utils.minio_utils for direct MinIO client operations.
"""

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel


class CredentialsResponse(BaseModel):
    """Response model for user credentials (internal use)"""

    username: Annotated[str, "Username"]
    access_key: Annotated[str, "MinIO access key (same as username)"]
    secret_key: Annotated[str, "MinIO secret key (fresh on each request)"]


class SharePathRequest(BaseModel):
    """Request model for sharing a path"""

    path: Annotated[str, "S3 path to share"]
    with_users: Annotated[List[str], "List of usernames to share with"] = []
    with_groups: Annotated[List[str], "List of group names to share with"] = []


class UnsharePathRequest(BaseModel):
    """Request model for unsharing a path"""

    path: Annotated[str, "S3 path to unshare"]
    from_users: Annotated[List[str], "List of usernames to remove access from"] = []
    from_groups: Annotated[List[str], "List of group names to remove access from"] = []


class SharePathResponse(BaseModel):
    """Response model for path sharing operations"""

    path: Annotated[str, "Path that was shared"]
    shared_with_users: Annotated[List[str], "Users successfully shared with"]
    shared_with_groups: Annotated[List[str], "Groups successfully shared with"]
    success_count: Annotated[int, "Total successful shares"]
    errors: Annotated[List[str], "Any errors encountered"] = []
    shared_by: Annotated[str, "User who performed the sharing"]
    shared_at: Annotated[datetime, "When sharing was performed"]


class UnsharePathResponse(BaseModel):
    """Response model for unsharing operations"""

    path: Annotated[str, "Path that was unshared"]
    unshared_from_users: Annotated[List[str], "Users successfully unshared from"]
    unshared_from_groups: Annotated[List[str], "Groups successfully unshared from"]
    success_count: Annotated[int, "Total successful unshares"]
    errors: Annotated[List[str], "Any errors encountered"] = []
    unshared_by: Annotated[str, "User who performed the unsharing"]
    unshared_at: Annotated[datetime, "When unsharing was performed"]


class PolicyInfo(BaseModel):
    """Model for policy information"""

    policy_name: Annotated[str, "Policy name"]
    policy_document: Annotated[Dict[str, Any], "Policy document"]


class UserWorkspaceResponse(BaseModel):
    """Response model for user workspace information"""

    username: Annotated[str, "Username"]
    access_key: Annotated[str, "MinIO access key"]
    secret_key: Annotated[Optional[str], "MinIO secret key"] = None
    home_paths: Annotated[List[str], "User's home directory paths"] = []
    groups: Annotated[List[str], "List of groups the user belongs to"] = []
    user_policies: Annotated[List[PolicyInfo], "User's policies (home and system)"] = []
    group_policies: Annotated[List[PolicyInfo], "Policies from associated groups"] = []
    total_policies: Annotated[int, "Total number of policies"] = 0
    accessible_paths: Annotated[List[str], "All paths accessible by the user"] = []


class UserPoliciesResponse(BaseModel):
    """Response model for user policies"""

    username: Annotated[str, "Username"]
    user_home_policy: Annotated[PolicyInfo, "User's home policy"]
    user_system_policy: Annotated[PolicyInfo, "User's system policy"]
    group_policies: Annotated[List[PolicyInfo], "Policies from group memberships"] = []
    total_policies: Annotated[int, "Number of active policies"]


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: Annotated[str, "Service status"]


class PathRequest(BaseModel):
    """Request model for S3 path operations"""

    path: Annotated[str, "S3 path for the operation"]


class PublicAccessResponse(BaseModel):
    """Response model for public/private access operations"""

    path: Annotated[str, "Path that was modified"]
    is_public: Annotated[bool, "Whether the path is now public"]


class PathAccessInfoResponse(BaseModel):
    """Response model for path access information"""

    path: Annotated[str, "Path that was queried"]
    users: Annotated[List[str], "Users with access to the path"]
    groups: Annotated[List[str], "Groups with access to the path"]
    public: Annotated[bool, "Whether the path is publicly accessible"]


class SqlWarehousePrefixResponse(BaseModel):
    """Response model for SQL warehouse prefix"""

    username: Annotated[str, "Username"]
    sql_warehouse_prefix: Annotated[str, "SQL warehouse prefix for the user"]


class GroupSqlWarehousePrefixResponse(BaseModel):
    """Response model for group's SQL warehouse prefix"""

    group_name: Annotated[str, "Group name"]
    sql_warehouse_prefix: Annotated[str, "SQL warehouse prefix for the group"]
