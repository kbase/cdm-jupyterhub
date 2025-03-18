"""Module for interacting with Spark databases and tables.

This module provides functions to retrieve information about databases, tables,
and their schemas from a Spark cluster.
"""

import json
from typing import Union, Dict, Optional, List, Any

from pyspark.sql import SparkSession

from spark.utils import get_spark_session


def _execute_with_spark(func: Any, spark: Optional[SparkSession] = None, *args, **kwargs) -> Any:
    """
    Execute a function with a SparkSession, creating one if not provided.
    """
    if spark is None:
        with get_spark_session() as spark:
            return func(spark, *args, **kwargs)
    return func(spark, *args, **kwargs)


def _format_output(data: Any, return_json: bool = True) -> Union[str, Any]:
    """
    Format the output based on the return_json flag.
    """
    return json.dumps(data) if return_json else data


def get_databases(spark: Optional[SparkSession] = None,
                 return_json: bool = True) -> Union[str, List[str]]:
    """
    Get the list of databases in the Spark session.
    
    Args:
        spark: Optional SparkSession to use
        return_json: Whether to return JSON string or raw data
    
    Returns:
        List of database names, either as JSON string or raw list
    """
    def _get_dbs(session: SparkSession) -> List[str]:
        return [db.name for db in session.catalog.listDatabases()]
    
    databases = _execute_with_spark(_get_dbs, spark)
    return _format_output(databases, return_json)


def get_tables(database: str,
               spark: Optional[SparkSession] = None,
               return_json: bool = True) -> Union[str, List[str]]:
    """
    Get the list of tables in a specific database.
    
    Args:
        database: Name of the database
        spark: Optional SparkSession to use
        return_json: Whether to return JSON string or raw data
    
    Returns:
        List of table names, either as JSON string or raw list
    """
    def _get_tbls(session: SparkSession, db: str) -> List[str]:
        return [table.name for table in session.catalog.listTables(dbName=db)]
    
    tables = _execute_with_spark(_get_tbls, spark, database)
    return _format_output(tables, return_json)


def get_table_schema(database: str,
                    table: str,
                    spark: Optional[SparkSession] = None,
                    return_json: bool = True) -> Union[str, List[str]]:
    """
    Get the schema of a specific table in a database.
    
    Args:
        database: Name of the database
        table: Name of the table
        spark: Optional SparkSession to use
        return_json: Whether to return JSON string or raw data
    
    Returns:
        List of column names, either as JSON string or raw list
    """
    def _get_schema(session: SparkSession, db: str, tbl: str) -> List[str]:
        try:
            return [column.name for column in session.catalog.listColumns(dbName=db, tableName=tbl)]
        except Exception as e:
            # Observed that certain tables lack their corresponding S3 files
            print(f"Error retrieving schema for table {tbl} in database {db}")
            return []
    
    columns = _execute_with_spark(_get_schema, spark, database, table)
    return _format_output(columns, return_json)


def get_db_structure(with_schema: bool = False,
                    return_json: bool = True) -> Union[str, Dict]:
    """
    Get the structure of all databases in the Spark session.
    
    Args:
        with_schema: Whether to include table schemas
        return_json: Whether to return JSON string or raw data
    
    Returns:
        Database structure as either JSON string or dictionary:
        {
            "database_name": ["table1", "table2"] or
            "database_name": {
                "table1": ["column1", "column2"],
                "table2": ["column1", "column2"]
            }
        }
    """
    def _get_structure(session: SparkSession) -> Dict[str, Union[List[str], Dict[str, List[str]]]]:
        db_structure = {}
        databases = get_databases(spark=session, return_json=False)
        
        for db in databases:
            tables = get_tables(database=db, spark=session, return_json=False)
            if with_schema:
                db_structure[db] = {
                    table: get_table_schema(database=db, table=table, spark=session, return_json=False)
                    for table in tables
                }
            else:
                db_structure[db] = tables
        
        return db_structure
    
    structure = _execute_with_spark(_get_structure)
    return _format_output(structure, return_json)
