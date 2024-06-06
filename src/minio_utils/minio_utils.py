"""
This module contains utility functions to interact with Minio.
"""

import os

from minio import Minio


def get_minio_client() -> Minio:
    """
    Helper function to get the Minio client.

    :return: A Minio client object
    """
    return Minio(
        os.environ['MINIO_URL'].replace("http://", ""),
        access_key=os.environ['MINIO_ACCESS_KEY'],
        secret_key=os.environ['MINIO_SECRET_KEY'],
        secure=False
    )
