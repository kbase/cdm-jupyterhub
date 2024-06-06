import os
from datetime import datetime
from threading import Timer

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession

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
        executor_cores: int) -> dict:
    """
    Helper function to get Delta Lake specific Spark configuration.

    :param jars_str: A comma-separated string of JAR file paths
    :param executor_cores: The number of CPU cores that each Spark executor will use

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
        "spark.executor.cores": executor_cores,
    }


def _stop_spark_session(spark):
    print("Stopping Spark session after timeout...")
    spark.stop()


def get_base_spark_conf(app_name: str) -> SparkConf:
    """
    Helper function to get the base Spark configuration.

    :param app_name: The name of the application

    :return: A SparkConf object with the base configuration
    """
    return SparkConf().setAll([
        ("spark.master", os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077")),
        ("spark.app.name", app_name),
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

    spark_conf = get_base_spark_conf(app_name)

    if delta_lake:

        # Just to include the necessary jars for Delta Lake
        jar_names = [f"delta-spark_{SCALA_VER}-{DELTA_SPARK_VER}.jar",
                     f"hadoop-aws-{HADOOP_AWS_VER}.jar"]
        jars_str = _get_jars(jar_names)
        delta_conf = _get_delta_lake_conf(jars_str, executor_cores)
        for key, value in delta_conf.items():
            spark_conf.set(key, value)

    spark = SparkSession.builder.config(conf=spark_conf).getOrCreate()
    timeout_sec = os.getenv('SPARK_TIMEOUT_SECONDS', timeout_sec)
    Timer(int(timeout_sec), _stop_spark_session, [spark]).start()

    return spark
