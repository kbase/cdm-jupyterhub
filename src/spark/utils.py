"""
Spark utilities for CDM JupyterHub.

This module provides utilities for creating and configuring Spark sessions
with support for Delta Lake, MinIO S3 storage, and fair scheduling.
"""

import csv
import os
import socket
from datetime import datetime
from typing import Dict, List, Optional

from pyspark.conf import SparkConf
from pyspark.sql import DataFrame, SparkSession

from minio_governance.client import DataGovernanceClient
from minio_utils.minio_utils import get_minio_client
from service.arg_checkers import not_falsy

# =============================================================================
# CONSTANTS
# =============================================================================

# JAR file configuration
JAR_DIR = "/opt/bitnami/spark/jars"

# Spark executor defaults
DEFAULT_EXECUTOR_CORES = 1
DEFAULT_EXECUTOR_MEMORY = "2g"
DEFAULT_MAX_EXECUTORS = 5

# Fair scheduler configuration
SPARK_DEFAULT_POOL = "default"
SPARK_POOLS = [SPARK_DEFAULT_POOL, "highPriority"]

# Delta Lake configuration
DEFAULT_DELTALAKE_WAREHOUSE_DIR = "s3a://cdm-lake/warehouse"

# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================


def _validate_env_vars(required_vars: List[str], context: str) -> None:
    """Validate that required environment variables are set."""
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables for {context}: {missing}"
        )


def _get_jars(jar_names: List[str]) -> str:
    """
    Get required JAR files as a comma-separated string.

    Args:
        jar_names: List of JAR file names

    Returns:
        Comma-separated string of JAR file paths

    Raises:
        FileNotFoundError: If any required JAR files are missing
    """
    jars = [os.path.join(JAR_DIR, jar) for jar in jar_names]

    missing_jars = [jar for jar in jars if not os.path.exists(jar)]
    if missing_jars:
        raise FileNotFoundError(f"Required JAR files not found: {missing_jars}")

    return ", ".join(jars)


def _get_s3_conf() -> Dict[str, str]:
    """
    Get S3 configuration for MinIO.

    Returns:
        Dictionary of S3/MinIO Spark configuration properties
    """
    # Set warehouse directory to the user's SQL warehouse
    governance_client = DataGovernanceClient()
    warehouse_dir = governance_client.get_sql_warehouse_prefix().sql_warehouse_prefix

    return {
        "spark.hadoop.fs.s3a.endpoint": str(
            not_falsy(os.environ.get("MINIO_URL"), "MINIO_URL")
        ),
        "spark.hadoop.fs.s3a.access.key": str(
            not_falsy(os.environ.get("MINIO_ACCESS_KEY"), "MINIO_ACCESS_KEY")
        ),
        "spark.hadoop.fs.s3a.secret.key": str(
            not_falsy(os.environ.get("MINIO_SECRET_KEY"), "MINIO_SECRET_KEY")
        ),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.sql.warehouse.dir": warehouse_dir,
    }


def _get_delta_lake_conf() -> Dict[str, str]:
    """
    Get Delta Lake specific Spark configuration.

    Returns:
        Dictionary of Delta Lake Spark configuration properties

    Reference:
        https://blog.min.io/delta-lake-minio-multi-cloud/
    """
    return {
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.databricks.delta.retentionDurationCheck.enabled": "false",
        "spark.sql.catalogImplementation": "hive",
    }


def _configure_dynamic_allocation(config: Dict[str, str]) -> None:
    """Configure Spark dynamic allocation settings."""
    config.update(
        {
            "spark.dynamicAllocation.enabled": "true",
            "spark.dynamicAllocation.minExecutors": "1",
            "spark.dynamicAllocation.maxExecutors": os.getenv(
                "MAX_EXECUTORS", str(DEFAULT_MAX_EXECUTORS)
            ),
            "spark.executor.cores": os.environ.get(
                "EXECUTOR_CORES", str(DEFAULT_EXECUTOR_CORES)
            ),
            "spark.executor.memory": os.getenv(
                "EXECUTOR_MEMORY", DEFAULT_EXECUTOR_MEMORY
            ),
        }
    )


def _configure_fair_scheduler(config: Dict[str, str]) -> None:
    """Configure Spark fair scheduler settings."""
    _validate_env_vars(["SPARK_FAIR_SCHEDULER_CONFIG"], "fair scheduler setup")
    config.update(
        {
            "spark.scheduler.mode": "FAIR",
            "spark.scheduler.allocation.file": os.environ[
                "SPARK_FAIR_SCHEDULER_CONFIG"
            ],
        }
    )


def _configure_driver_host(config: Dict[str, str]) -> None:
    """Configure Spark driver host settings."""
    _validate_env_vars(["SPARK_DRIVER_HOST"], "Spark driver setup")
    hostname = os.environ["SPARK_DRIVER_HOST"]

    if os.environ.get("USE_KUBE_SPAWNER") == "true":
        # For Kubernetes: use pod IP since hostname may not be resolvable
        config["spark.driver.host"] = socket.gethostbyname(hostname)
    else:
        # For Docker/standalone: hostname is resolvable
        config["spark.driver.host"] = hostname


def _configure_spark_master(config: Dict[str, str]) -> None:
    """Configure Spark master URL."""
    _validate_env_vars(["SPARK_MASTER_URL"], "Spark master setup")
    config["spark.master"] = os.environ["SPARK_MASTER_URL"]


def _configure_delta_lake(config: Dict[str, str]) -> None:
    """Configure Delta Lake support including JARs and settings."""
    _validate_env_vars(
        ["HADOOP_AWS_VER", "DELTA_SPARK_VER", "SCALA_VER"], "Delta Lake setup"
    )

    # Add Delta Lake configuration
    config.update(_get_delta_lake_conf())

    # Add required JAR files
    jars = _get_jars(
        [
            f"delta-spark_{os.environ['SCALA_VER']}-{os.environ['DELTA_SPARK_VER']}.jar",
            f"hadoop-aws-{os.environ['HADOOP_AWS_VER']}.jar",
        ]
    )
    config["spark.jars"] = jars


def _set_scheduler_pool(spark: SparkSession, scheduler_pool: str) -> None:
    """Set the scheduler pool for the Spark session."""
    if scheduler_pool not in SPARK_POOLS:
        print(
            f"Warning: Scheduler pool '{scheduler_pool}' not in available pools: {SPARK_POOLS}. "
            f"Defaulting to '{SPARK_DEFAULT_POOL}'"
        )
        scheduler_pool = SPARK_DEFAULT_POOL

    spark.sparkContext.setLocalProperty("spark.scheduler.pool", scheduler_pool)


def _detect_csv_delimiter(sample: str) -> str:
    """
    Detect CSV delimiter from a sample string.

    Args:
        sample: Sample string from CSV file

    Returns:
        Detected delimiter character

    Raises:
        ValueError: If delimiter cannot be detected
    """
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
        return dialect.delimiter
    except Exception as e:
        raise ValueError(
            f"Could not detect CSV delimiter: {e}. Please provide delimiter explicitly."
        ) from e


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================


def get_spark_session(
    app_name: Optional[str] = None,
    local: bool = False,
    delta_lake: bool = True,
    scheduler_pool: str = SPARK_DEFAULT_POOL,
) -> SparkSession:
    """
    Create and configure a Spark session with CDM-specific settings.

    This function creates a Spark session configured for the CDM environment,
    including support for Delta Lake, MinIO S3 storage, and fair scheduling.

    Args:
        app_name: Application name. If None, generates a timestamp-based name
        local: If True, creates a local Spark session (ignores other configs)
        delta_lake: If True, enables Delta Lake support with required JARs
        scheduler_pool: Fair scheduler pool name (default: "default")

    Returns:
        Configured SparkSession instance

    Raises:
        EnvironmentError: If required environment variables are missing
        FileNotFoundError: If required JAR files are missing

    Example:
        >>> # Basic usage
        >>> spark = get_spark_session("MyApp")

        >>> # With custom scheduler pool
        >>> spark = get_spark_session("MyApp", scheduler_pool="highPriority")

        >>> # Local development
        >>> spark = get_spark_session("TestApp", local=True)
    """
    # Generate app name if not provided
    if app_name is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        app_name = f"kbase_spark_session_{timestamp}"

    # For local development, return simple session
    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    # Build configuration dictionary
    config: Dict[str, str] = {"spark.app.name": app_name}

    # Configure core Spark settings
    _configure_dynamic_allocation(config)
    _configure_fair_scheduler(config)
    _configure_driver_host(config)
    _configure_spark_master(config)

    # Configure Delta Lake if enabled
    if delta_lake:
        config.update(_get_s3_conf())
        _configure_delta_lake(config)

    # Create and configure Spark session
    spark_conf = SparkConf().setAll(list(config.items()))
    spark = SparkSession.builder.config(conf=spark_conf).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    # Set scheduler pool
    _set_scheduler_pool(spark, scheduler_pool)

    return spark


def read_csv(
    spark: SparkSession,
    path: str,
    header: bool = True,
    sep: Optional[str] = None,
    minio_url: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    **kwargs,
) -> DataFrame:
    """
    Read CSV file from MinIO into a Spark DataFrame with automatic delimiter detection.

    Args:
        spark: Spark session instance
        path: MinIO path to CSV file (e.g., "s3a://bucket/file.csv" or "bucket/file.csv")
        header: Whether CSV file has header row
        sep: CSV delimiter. If None, will attempt auto-detection
        minio_url: MinIO URL (uses MINIO_URL env var if None)
        access_key: MinIO access key (uses MINIO_ACCESS_KEY env var if None)
        secret_key: MinIO secret key (uses MINIO_SECRET_KEY env var if None)
        **kwargs: Additional arguments passed to spark.read.csv()

    Returns:
        Spark DataFrame containing CSV data

    Example:
        >>> # Basic usage with auto-detection
        >>> df = read_csv(spark, "s3a://my-bucket/data.csv")

        >>> # With explicit delimiter
        >>> df = read_csv(spark, "s3a://my-bucket/data.tsv", sep="\\t")

        >>> # With custom MinIO credentials
        >>> df = read_csv(
        ...     spark,
        ...     "s3a://my-bucket/data.csv",
        ...     minio_url="http://localhost:9000",
        ...     access_key="my-key",
        ...     secret_key="my-secret"
        ... )
    """
    # Auto-detect delimiter if not provided
    if sep is None:
        client = get_minio_client(
            minio_url=minio_url, access_key=access_key, secret_key=secret_key
        )

        # Parse S3 path to get bucket and key
        s3_path = path.replace("s3a://", "")
        bucket, key = s3_path.split("/", 1)

        # Sample file to detect delimiter
        obj = client.get_object(bucket, key)
        sample = obj.read(8192).decode()
        sep = _detect_csv_delimiter(sample)
        print(f"Auto-detected CSV delimiter: '{sep}'")

    # Read CSV into DataFrame
    return spark.read.csv(path, header=header, sep=sep, **kwargs)
