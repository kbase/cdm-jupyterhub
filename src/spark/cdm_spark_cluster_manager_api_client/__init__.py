"""A client library for accessing CDM Spark Cluster Manager API"""

from .client import AuthenticatedClient, Client

__all__ = (
    "AuthenticatedClient",
    "Client",
)
