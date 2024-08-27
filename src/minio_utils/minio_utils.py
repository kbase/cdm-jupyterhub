"""
This module contains utility functions to interact with Minio.
"""

import os

from minio import Minio


def get_minio_client(
        minio_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        secure: bool = False
) -> Minio:
    """
    Helper function to get the Minio client.

    :param minio_url: URL for the Minio server (environment variable used if not provided)
    :param access_key: Access key for Minio (environment variable used if not provided)
    :param secret_key: Secret key for Minio (environment variable used if not provided)
    :param secure: Whether to use HTTPS (optional, default is False)
    :return: A Minio client object
    """
    minio_url = minio_url or os.environ['MINIO_URL'].replace("http://", "")
    access_key = access_key or os.environ['MINIO_ACCESS_KEY']
    secret_key = secret_key or os.environ['MINIO_SECRET_KEY']

    return Minio(
        minio_url,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )
