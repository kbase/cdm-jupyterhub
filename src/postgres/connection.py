"""PostgreSQL connection management module."""

import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


def get_postgres_connection(dbname: Optional[str] = None,
                            user: Optional[str] = None,
                            password: Optional[str] = None,
                            host: Optional[str] = None,
                            port: Optional[str] = None):
    """Get a connection to the PostgreSQL database.

    Args:
        dbname: Database name (defaults to POSTGRES_DB env var)
        user: Database user (defaults to POSTGRES_USER env var)
        password: Database password (defaults to POSTGRES_PASSWORD env var)
        host: Database host (defaults to host in POSTGRES_URL env var)
        port: Database port (defaults to port in POSTGRES_URL env var)

    Returns:
        A PostgreSQL connection with RealDictCursor
    """
    postgres_url = os.environ.get('POSTGRES_URL', '')
    if ':' not in postgres_url:
        raise ValueError("POSTGRES_URL must be in the format 'host:port'")
    default_host, default_port = postgres_url.split(':')

    # Get connection parameters
    db_params = {
        'dbname': dbname or os.environ.get('POSTGRES_DB'),
        'user': user or os.environ.get('POSTGRES_USER'),
        'password': password or os.environ.get('POSTGRES_PASSWORD'),
        'host': host or default_host,
        'port': port or default_port,
        'cursor_factory': RealDictCursor
    }

    try:
        return psycopg2.connect(**db_params)
    except psycopg2.Error as e:
        raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e
