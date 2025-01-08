import csv
import os
import site
from datetime import datetime
from threading import Timer
from urllib.parse import urlparse

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession, DataFrame

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


def _get_s3_conf() -> dict:
    return {
        "spark.hadoop.fs.s3a.endpoint": os.environ.get("MINIO_URL"),
        "spark.hadoop.fs.s3a.access.key": os.environ.get("MINIO_ACCESS_KEY"),
        "spark.hadoop.fs.s3a.secret.key": os.environ.get("MINIO_SECRET_KEY"),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    }

def _get_delta_lake_conf() -> dict:
    """
    Helper function to get Delta Lake specific Spark configuration.

    :return: A dictionary of Delta Lake specific Spark configuration

    reference: https://blog.min.io/delta-lake-minio-multi-cloud/
    """

    site_packages_path = site.getsitepackages()[0]

    return {
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.databricks.delta.retentionDurationCheck.enabled": "false",
        "spark.sql.catalogImplementation": "hive",
    }


def _get_base_spark_conf(
        app_name: str,
        executor_cores: int,
        yarn: bool
) -> SparkConf:
    """
    Helper function to get the base Spark configuration.

    :param app_name: The name of the application
    :param executor_cores: The number of CPU cores that each Spark executor will use.

    :return: A SparkConf object with the base configuration
    """
    sc = SparkConf().set("spark.app.name", app_name).set("spark.executor.cores", executor_cores)
    if yarn:
        yarnparse = urlparse(os.environ.get("YARN_RESOURCE_MANAGER_URL"))
        sc.setMaster("yarn"
            ).set("spark.hadoop.yarn.resourcemanager.hostname", yarnparse.hostname
            ).set("spark.hadoop.yarn.resourcemanager.address", yarnparse.netloc)
    else:
        sc.set("spark.master", os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077"))
    return sc


def get_spark_session(
        app_name: str = None,
        local: bool = False,
        yarn: bool = True,
        delta_lake: bool = True,
        executor_cores: int = DEFAULT_EXECUTOR_CORES) -> SparkSession:
    """
    Helper to get and manage the SparkSession and keep all of our spark configuration params in one place.

    :param app_name: The name of the application. If not provided, a default name will be generated.
    :param local: Whether to run the spark session locally or not. Default is False.
    :param yarn: Whether to run the spark session on YARN or not. Default is True.
    :param delta_lake: Build the spark session with Delta Lake support. Default is True.
    :param executor_cores: The number of CPU cores that each Spark executor will use. Default is 1.

    :return: A SparkSession object
    """
    if not app_name:
        app_name = f"kbase_spark_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    spark_conf = _get_base_spark_conf(app_name, executor_cores, yarn)
    sc = {}
    if delta_lake or yarn:
        sc.update(_get_s3_conf())
    if yarn:
        sc["spark.yarn.stagingDir"] = "s3a://" + os.environ["S3_YARN_BUCKET"]

    if delta_lake:

        # Just to include the necessary jars for Delta Lake
        jar_names = [f"delta-spark_{SCALA_VER}-{DELTA_SPARK_VER}.jar",
                     f"hadoop-aws-{HADOOP_AWS_VER}.jar"]
        if not yarn:
            sc["spark.jars"] = _get_jars(jar_names)
        sc.update(_get_delta_lake_conf())

    for key, value in sc.items():
        spark_conf.set(key, value)
    spark = SparkSession.builder.config(conf=spark_conf).getOrCreate()

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
        minio_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        **kwargs
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
        client = get_minio_client(minio_url=minio_url, access_key=access_key, secret_key=secret_key)
        bucket, key = path.replace("s3a://", "").split("/", 1)
        obj = client.get_object(bucket, key)
        sample = obj.read(8192).decode()
        sep = _detect_delimiter(sample)
        print(f"Detected delimiter: {sep}")

    df = spark.read.csv(path, header=header, sep=sep, **kwargs)

    return df
