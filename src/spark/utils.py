import csv
import os
import socket
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

from pyspark.conf import SparkConf
from pyspark.sql import DataFrame, SparkSession

from minio_utils.minio_utils import get_minio_client
from service.arg_checkers import not_falsy

# Default directory for JAR files in the Bitnami Spark image
JAR_DIR = "/opt/bitnami/spark/jars"
# the default number of CPU cores that each Spark executor will use
# If not specified, Spark will typically use all available cores on the worker nodes
DEFAULT_EXECUTOR_CORES = 1
# Available Spark fair scheduler pools are defined in /config/spark-fairscheduler.xml
SPARK_DEFAULT_POOL = "default"
SPARK_POOLS = [SPARK_DEFAULT_POOL, "highPriority"]
DEFAULT_MAX_EXECUTORS = 5
# Alternatively, use a local directory for the Hive metastore, e.g., /cdm_shared_workspace/hive_metastore
DEFAULT_DELTALAKE_WAREHOUSE_DIR = "s3a://cdm-lake/warehouse"


def _get_jars(jar_names: List[str]) -> str:
    """
    Helper function to get the required JAR files as a comma-separated string.

    :param jar_names: List of JAR file names

    :return: A comma-separated string of JAR file paths
    """
    jars = [os.path.join(JAR_DIR, jar) for jar in jar_names]

    missing_jars = [jar for jar in jars if not os.path.exists(jar)]
    if missing_jars:
        raise FileNotFoundError(f"Some required jars are not found: {missing_jars}")

    return ", ".join(jars)


def _get_s3_conf() -> Dict[str, str]:
    """
    Helper function to get S3 configuration for MinIO.
    """
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
        # When Hive integration is enabled (by default), the hive.metastore.warehouse.dir property takes precedence over
        # spark.sql.warehouse.dir for managed tables. The Hive property is defined in the hive-site.xml configuration file 
        # from the cdm-spark-standalone image.
        "spark.sql.warehouse.dir": os.environ.get(
            "DELTALAKE_WAREHOUSE_DIR", DEFAULT_DELTALAKE_WAREHOUSE_DIR
        ),
    }


def _get_delta_lake_conf() -> Dict[str, str]:
    """
    Helper function to get Delta Lake specific Spark configuration.

    :return: A dictionary of Delta Lake specific Spark configuration

    reference: https://blog.min.io/delta-lake-minio-multi-cloud/
    """

    return {
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.databricks.delta.retentionDurationCheck.enabled": "false",
        "spark.sql.catalogImplementation": "hive",
    }


def _validate_env_vars(required_vars: List[str], context: str) -> None:
    """Validate required environment variables."""
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables for {context}: {missing}"
        )


def get_spark_session(
    app_name: str | None = None,
    local: bool = False,
    yarn: bool = True,
    delta_lake: bool = True,
    executor_cores: int = DEFAULT_EXECUTOR_CORES,
    scheduler_pool: str = SPARK_DEFAULT_POOL,
) -> SparkSession:
    """
    Helper to get and manage the SparkSession and keep all of our spark configuration params in one place.

    :param app_name: The name of the application. If not provided, a default name will be generated.
    :param local: Whether to run the spark session locally or not. Default is False.
    :param yarn: Whether to run the spark session on YARN or not. Default is True.
    :param delta_lake: Build the spark session with Delta Lake support. Default is True.
    :param executor_cores: The number of CPU cores that each Spark executor will use. Default is 1.
    :param scheduler_pool: The name of the scheduler pool to use. Default is "default".

    :return: A SparkSession object
    """

    app_name = (
        app_name or f"kbase_spark_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    config: Dict[str, str] = {
        "spark.app.name": app_name,
        "spark.executor.cores": str(executor_cores),
    }

    # Dynamic allocation configuration
    config.update(
        {
            "spark.dynamicAllocation.enabled": "true",
            "spark.dynamicAllocation.minExecutors": "1",
            "spark.dynamicAllocation.maxExecutors": os.getenv(
                "MAX_EXECUTORS", str(DEFAULT_MAX_EXECUTORS)
            ),
        }
    )

    # Fair scheduler configuration
    _validate_env_vars(["SPARK_FAIR_SCHEDULER_CONFIG"], "FAIR scheduler setup")
    config.update(
        {
            "spark.scheduler.mode": "FAIR",
            "spark.scheduler.allocation.file": os.environ[
                "SPARK_FAIR_SCHEDULER_CONFIG"
            ],
        }
    )

    # Kubernetes configuration
    _validate_env_vars(["SPARK_DRIVER_HOST"], "Kubernetes setup")
    hostname = os.environ["SPARK_DRIVER_HOST"]
    if os.environ.get("USE_KUBE_SPAWNER") == "true":
        yarn = False  # YARN is not used in the Kubernetes spawner
        # Since the Spark driver cannot resolve a pod's hostname without a dedicated service for each user pod,
        # use the pod IP as the identifier for the Spark driver host
        config["spark.driver.host"] = socket.gethostbyname(hostname)
    else:
        # General driver host configuration - hostname is resolvable
        config["spark.driver.host"] = hostname

    # YARN configuration
    if yarn:
        _validate_env_vars(
            ["YARN_RESOURCE_MANAGER_URL", "S3_YARN_BUCKET"], "YARN setup"
        )
        yarnparse = urlparse(os.environ["YARN_RESOURCE_MANAGER_URL"])

        config.update(
            {
                "spark.master": "yarn",
                "spark.hadoop.yarn.resourcemanager.hostname": str(yarnparse.hostname),
                "spark.hadoop.yarn.resourcemanager.address": yarnparse.netloc,
                "spark.yarn.stagingDir": f"s3a://{os.environ['S3_YARN_BUCKET']}",
            }
        )
    else:
        _validate_env_vars(["SPARK_MASTER_URL"], "Standalone Spark setup")
        config["spark.master"] = os.environ["SPARK_MASTER_URL"]

    # S3 configuration
    if yarn or delta_lake:
        config.update(_get_s3_conf())

    # Delta Lake configuration
    if delta_lake:
        _validate_env_vars(
            ["HADOOP_AWS_VER", "DELTA_SPARK_VER", "SCALA_VER"], "Delta Lake setup"
        )
        config.update(_get_delta_lake_conf())

        if not yarn:
            jars = _get_jars(
                [
                    f"delta-spark_{os.environ['SCALA_VER']}-{os.environ['DELTA_SPARK_VER']}.jar",
                    f"hadoop-aws-{os.environ['HADOOP_AWS_VER']}.jar",
                ]
            )
            config["spark.jars"] = jars

    # Create SparkConf from accumulated configuration
    spark_conf = SparkConf().setAll(list(config.items()))

    # Initialize SparkSession
    spark = SparkSession.builder.config(conf=spark_conf).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    # Configure scheduler pool
    if scheduler_pool not in SPARK_POOLS:
        print(
            f"Warning: Scheduler pool {scheduler_pool} is not in the list of available pools: {SPARK_POOLS} "
            f"Defaulting to {SPARK_DEFAULT_POOL} pool"
        )
        scheduler_pool = SPARK_DEFAULT_POOL
    spark.sparkContext.setLocalProperty("spark.scheduler.pool", scheduler_pool)

    return spark


def _detect_delimiter(sample: str) -> str:
    """
    Detect the delimiter of a CSV file from a sample string.

    :param sample: A sample string from the CSV file

    :return: The detected delimiter or raise error if it cannot be detected
    """

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
        return dialect.delimiter
    except Exception as e:
        raise ValueError(
            f"Delimiter could not be detected: {e}. Please provide the delimiter explicitly."
        ) from e


def read_csv(
    spark: SparkSession,
    path: str,
    header: bool = True,
    sep: str | None = None,
    minio_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    **kwargs,
) -> DataFrame:
    """
    Read a file in CSV format from minIO into a Spark DataFrame.

    :param spark: The Spark session.
    :param path: The minIO path to the CSV file. e.g. s3a://bucket-name/file.csv or bucket-name/file.csv
    :param header: Whether the CSV file has a header. Default is True.
    :param sep: The delimiter to use. If not provided, the function will try to detect it.
    :param minio_url: The minIO URL. Default is None (environment variable used if not provided).
    :param access_key: The minIO access key. Default is None (environment variable used if not provided).
    :param secret_key: The minIO secret key. Default is None (environment variable used if not provided).
    :param kwargs: Additional arguments to pass to spark.read.csv.

    :return: A DataFrame.
    """

    if not sep:
        client = get_minio_client(
            minio_url=minio_url, access_key=access_key, secret_key=secret_key
        )
        bucket, key = path.replace("s3a://", "").split("/", 1)
        obj = client.get_object(bucket, key)
        sample = obj.read(8192).decode()
        sep = _detect_delimiter(sample)
        print(f"Detected delimiter: {sep}")

    df = spark.read.csv(path, header=header, sep=sep, **kwargs)

    return df
