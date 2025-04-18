from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.spark_cluster_config import SparkClusterConfig
from ...models.spark_cluster_create_response import SparkClusterCreateResponse
from ...types import Response


def _get_kwargs(
    *,
    body: SparkClusterConfig,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/clusters",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[SparkClusterCreateResponse]:
    if response.status_code == 201:
        response_201 = SparkClusterCreateResponse.from_dict(response.json())

        return response_201
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[SparkClusterCreateResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: SparkClusterConfig,
) -> Response[SparkClusterCreateResponse]:
    """Create a new Spark cluster

     Creates a new Spark cluster for the authenticated user with the specified configuration.

    Args:
        body (SparkClusterConfig): Configuration for creating a new Spark cluster.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SparkClusterCreateResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: SparkClusterConfig,
) -> Optional[SparkClusterCreateResponse]:
    """Create a new Spark cluster

     Creates a new Spark cluster for the authenticated user with the specified configuration.

    Args:
        body (SparkClusterConfig): Configuration for creating a new Spark cluster.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SparkClusterCreateResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: SparkClusterConfig,
) -> Response[SparkClusterCreateResponse]:
    """Create a new Spark cluster

     Creates a new Spark cluster for the authenticated user with the specified configuration.

    Args:
        body (SparkClusterConfig): Configuration for creating a new Spark cluster.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SparkClusterCreateResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: SparkClusterConfig,
) -> Optional[SparkClusterCreateResponse]:
    """Create a new Spark cluster

     Creates a new Spark cluster for the authenticated user with the specified configuration.

    Args:
        body (SparkClusterConfig): Configuration for creating a new Spark cluster.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SparkClusterCreateResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
