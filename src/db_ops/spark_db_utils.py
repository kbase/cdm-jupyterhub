"""
This module contains utility functions to interact with the Spark catalog.

"""

from pyspark.sql import SparkSession


def create_namespace_if_not_exists(
        spark: SparkSession,
        namespace: str = "default"
) -> None:

    """
    Create a namespace in the Spark catalog if it does not exist.

    :param spark: The Spark session.
    :param namespace: The name of the namespace. Default is "default".
    :return: None
    """
    try:
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {namespace}")
        print(f"Namespace {namespace} is ready to use.")
    except Exception as e:
        print(f"Error creating namespace {namespace}: {e}")


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

    try:
        spark.sql(f"DROP TABLE IF EXISTS {spark_catalog}")
        print(f"Table {spark_catalog} removed.")
    except Exception as e:
        print(f"Error removing table {spark_catalog}: {e}")

