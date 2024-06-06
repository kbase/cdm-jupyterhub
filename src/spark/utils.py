import csv
import os
from datetime import datetime
from threading import Timer

from pyspark.conf import SparkConf
from pyspark.pandas import DataFrame
from pyspark.sql import SparkSession

from minio_utils.minio_utils import get_minio_client

# Default directory for JAR files in the Bitnami Spark image
JAR_DIR = '/opt/bitnami/spark/jars'
HADOOP_AWS_VER = os.getenv('HADOOP_AWS_VER')
DELTA_SPARK_VER = os.getenv('DELTA_SPARK_VER')
SCALA_VER = os.getenv('SCALA_VER')
# the default number of CPU cores that each Spark executor will use
# If not specified, Spark will typically use all available cores on the worker nodes
DEFAULT_EXECUTOR_CORES = 1


def _get_jars(jar_names: list) -> str:
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


def _get_delta_lake_conf(
        jars_str: str,
) -> dict:
    """
    Helper function to get Delta Lake specific Spark configuration.

    :param jars_str: A comma-separated string of JAR file paths

    :return: A dictionary of Delta Lake specific Spark configuration

    reference: https://blog.min.io/delta-lake-minio-multi-cloud/
    """
    return {
        "spark.jars": jars_str,
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.databricks.delta.retentionDurationCheck.enabled": "false",
        "spark.hadoop.fs.s3a.endpoint": os.environ.get("MINIO_URL"),
        "spark.hadoop.fs.s3a.access.key": os.environ.get("MINIO_ACCESS_KEY"),
        "spark.hadoop.fs.s3a.secret.key": os.environ.get("MINIO_SECRET_KEY"),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.sql.catalogImplementation": "hive",
    }


def _stop_spark_session(spark):
    print("Stopping Spark session after timeout...")
    spark.stop()


def _get_base_spark_conf(
        app_name: str,
        executor_cores: int,
) -> SparkConf:
    """
    Helper function to get the base Spark configuration.

    :param app_name: The name of the application
    :param executor_cores: The number of CPU cores that each Spark executor will use.

    :return: A SparkConf object with the base configuration
    """
    return SparkConf().setAll([
        ("spark.master", os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077")),
        ("spark.app.name", app_name),
        ("spark.executor.cores", executor_cores),
    ])


def get_spark_session(
        app_name: str = None,
        local: bool = False,
        delta_lake: bool = True,
        timeout_sec: int = 4 * 60 * 60,
        executor_cores: int = DEFAULT_EXECUTOR_CORES) -> SparkSession:
    """
    Helper to get and manage the SparkSession and keep all of our spark configuration params in one place.

    :param app_name: The name of the application. If not provided, a default name will be generated.
    :param local: Whether to run the spark session locally or not. Default is False.
    :param delta_lake: Build the spark session with Delta Lake support. Default is True.
    :param timeout_sec: The timeout in seconds to stop the Spark session forcefully. Default is 4 hours.
    :param executor_cores: The number of CPU cores that each Spark executor will use. Default is 1.

    :return: A SparkSession object
    """
    if not app_name:
        app_name = f"kbase_spark_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    spark_conf = _get_base_spark_conf(app_name, executor_cores)

    if delta_lake:

        # Just to include the necessary jars for Delta Lake
        jar_names = [f"delta-spark_{SCALA_VER}-{DELTA_SPARK_VER}.jar",
                     f"hadoop-aws-{HADOOP_AWS_VER}.jar"]
        jars_str = _get_jars(jar_names)
        delta_conf = _get_delta_lake_conf(jars_str)
        for key, value in delta_conf.items():
            spark_conf.set(key, value)

    spark = SparkSession.builder.config(conf=spark_conf).getOrCreate()
    timeout_sec = os.getenv('SPARK_TIMEOUT_SECONDS', timeout_sec)
    Timer(int(timeout_sec), _stop_spark_session, [spark]).start()

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
            f"Delimiter could not be detected: {e}. Please provide the delimiter explicitly.") from e


def read_csv(
        spark: SparkSession,
        path: str,
        header: bool = True,
        sep: str = None,
        **kwargs
) -> DataFrame:
    """
    Read a file in CSV format from minIO into a Spark DataFrame.

    :param spark: The Spark session.
    :param path: The minIO path to the CSV file. e.g. s3a://bucket-name/file.csv or bucket-name/file.csv
    :param header: Whether the CSV file has a header. Default is True.
    :param sep: The delimiter to use. If not provided, the function will try to detect it.
    :param kwargs: Additional arguments to pass to spark.read.csv.

    :return: A DataFrame.
    """

    if not sep:
        client = get_minio_client()
        bucket, key = path.replace("s3a://", "").split("/", 1)
        obj = client.get_object(bucket, key)
        sample = obj.read(8192).decode()
        sep = _detect_delimiter(sample)
        print(f"Detected delimiter: {sep}")

    df = spark.read.csv(path, header=header, sep=sep, **kwargs)

    return df
