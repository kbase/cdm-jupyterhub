"""Module for querying Hive metastore information from PostgreSQL."""

from typing import List, cast

from psycopg2.extras import RealDictRow

from postgres.connection import get_postgres_connection


def get_databases() -> List[str]:
    """Get list of databases from Hive metastore.
    
    Returns:
        List of database names
    """
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT "NAME" FROM "DBS"''')
            rows = cast(List[RealDictRow], cur.fetchall())
            return [str(row.get('NAME')) for row in rows]


def get_tables(database: str) -> List[str]:
    """Get list of tables in a database from Hive metastore.
    
    Args:
        database: Name of the database
    
    Returns:
        List of table names
    """
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT "TBL_NAME" 
                FROM "TBLS" t 
                JOIN "DBS" d ON t."DB_ID" = d."DB_ID" 
                WHERE d."NAME" = %s
            ''', (database,))
            rows = cast(List[RealDictRow], cur.fetchall())
            return [str(row.get('TBL_NAME')) for row in rows]


def get_table_schema(database: str, table: str) -> List[str]:
    """Get schema of a table in a database from Hive metastore.

    Args:
        database: Name of the database
        table: Name of the table
    Returns:
        List of column names
    """

    raise NotImplementedError("This function is not implemented yet.")
