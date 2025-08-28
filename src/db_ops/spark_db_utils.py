"""
This module contains utility functions to interact with the Spark catalog.

"""

from pyspark.sql import SparkSession


def create_namespace_if_not_exists(
        spark: SparkSession,
        namespace: str = "default",
        append_target: bool = True,
) -> str:

    """
    Create a namespace in the Spark catalog if it does not exist.
    
    If append_target is True, automatically prepends the target name (user/tenant)
    from the Spark warehouse configuration to create {target_name}_{namespace}.

    :param spark: The Spark session.
    :param namespace: The name of the namespace.
    :param append_target: If True, prepends target name from warehouse directory
                         (e.g., "john_default" or "research_team_experiments").
                         If False, uses namespace as-is.
    :return: The name of the namespace.
    """
    try:
        # Extract user/tenant name from warehouse directory if append_target is enabled
        if append_target:
            warehouse_dir = spark.conf.get('spark.sql.warehouse.dir', '')
            
            if warehouse_dir and ('users-sql-warehouse' in warehouse_dir or 'tenant-sql-warehouse' in warehouse_dir):
                # Extract target name (username or tenant name) from path
                # e.g. s3a://cdm-lake/users-sql-warehouse/tgu2
                # e.g. s3a://cdm-lake/tenant-sql-warehouse/global-user-group
                target_name = warehouse_dir.rstrip('/').split('/')[-1]
                # Sanitize target_name to only contain valid characters (alphanumeric and underscore)
                sanitized_target_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in target_name)
                namespace = f"{sanitized_target_name}_{namespace}"
            else:
                # Keep original namespace if warehouse path doesn't match expected patterns
                print(f"Warning: Could not determine target name from warehouse directory '{warehouse_dir}'. Using namespace as-is.")
    except Exception as e:
        print(f"Error creating namespace: {e}")
        raise e
    
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {namespace}")
    print(f"Namespace {namespace} is ready to use.")

    return namespace


def table_exists(
        spark: SparkSession,
        table_name: str,
        namespace: str = "default",
) -> bool:

    """
    Check if a table exists in the Spark catalog.

    :param spark: The Spark session.
    :param table_name: The name of the table.
    :param namespace: The namespace of the table. Default is "default".
    :return: True if the table exists, False otherwise.
    """

    spark_catalog = f"{namespace}.{table_name}"

    try:
        spark.table(spark_catalog)
        print(f"Table {spark_catalog} exists.")
        return True
    except Exception as e:
        print(f"Table {spark_catalog} does not exist: {e}")
        return False


def remove_table(
        spark: SparkSession,
        table_name: str,
        namespace: str = "default",
) -> None:

    """
    Remove a table from the Spark catalog.

    :param spark: The Spark session.
    :param table_name: The name of the table.
    :param namespace: The namespace of the table. Default is "default".
    :return: None
    """

    spark_catalog = f"{namespace}.{table_name}"

    spark.sql(f"DROP TABLE IF EXISTS {spark_catalog}")
    print(f"Table {spark_catalog} removed.")

