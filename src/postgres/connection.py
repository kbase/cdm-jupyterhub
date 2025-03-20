"""PostgreSQL connection management module."""

import os
from typing import Optional, Any

import psycopg
from psycopg.rows import dict_row


def _validate_not_empty(value: Any, name: str, env_var: Optional[str] = None) -> Any:
    """Validate that a value is not None or empty string.

    Args:
        value: The value to validate
        name: Name of the parameter for error messages
        env_var: Optional environment variable name for error messages

    Raises:
        ValueError: If the value is None or empty string
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        msg = f"{name} must not be empty"
        if env_var:
            msg += f" (provide as parameter or set {env_var} env var)"
        raise ValueError(msg)

    return value


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
        A PostgreSQL connection with dict_row row factory

    Raises:
        ValueError: If POSTGRES_URL environment variable is not properly formatted
        psycopg.Error: If connection to the database fails
    """

    default_host, default_port = None, None
    if not host and not port:
        postgres_url = os.environ.get('POSTGRES_URL', '')
        if ':' not in postgres_url:
            raise ValueError("POSTGRES_URL must be in the format 'host:port'")
        default_host, default_port = postgres_url.split(':')

    # Get and validate connection parameters
    final_host = _validate_not_empty(host or default_host, "Database host", "POSTGRES_URL")
    final_port = _validate_not_empty(port or default_port, "Database port", "POSTGRES_URL")
    final_dbname = _validate_not_empty(dbname or os.environ.get('POSTGRES_DB'), "Database name", "POSTGRES_DB")
    final_user =  _validate_not_empty(user or os.environ.get('POSTGRES_USER'), "Database user", "POSTGRES_USER")
    final_password =  _validate_not_empty(password or os.environ.get('POSTGRES_PASSWORD'), "Database password", "POSTGRES_PASSWORD")

    # Get connection parameters
    db_params = {
        'dbname': final_dbname,
        'user': final_user,
        'password': final_password,
        'host': final_host,
        'port': final_port,
        'row_factory': dict_row
    }

    try:
        return psycopg.connect(**db_params)
    except psycopg.Error as e:
        error_context = (
            f"Failed to connect to PostgreSQL at {final_host}:{final_port} "
            f"(database: {final_dbname}, user: {final_user})"
        )
        raise ConnectionError(f"{error_context}: {str(e)}") from e
