import os

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession

# Default directory for JAR files in the Bitnami Spark image
JAR_DIR = '/opt/bitnami/spark/jars'
HADOOP_AWS_VER = os.getenv('HADOOP_AWS_VER')
DELTA_SPARK_VER = os.getenv('DELTA_SPARK_VER')
SCALA_VER = os.getenv('SCALA_VER')


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


def _get_delta_lake_conf(jars_str: str) -> dict:
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
        app_name: str,
        local: bool = False,
        delta_lake: bool = False) -> SparkSession:
    """
    Helper to get and manage the SparkSession and keep all of our spark configuration params in one place.

    :param app_name: The name of the application
    :param local: Whether to run the spark session locally or not
    :param delta_lake: Build the spark session with Delta Lake support

    :return: A SparkSession object
    """
    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    spark_conf = get_base_spark_conf(app_name)

    if delta_lake:

        # Just to include the necessary jars for Delta Lake
        jar_names = [f"delta-spark_{SCALA_VER}-{DELTA_SPARK_VER}.jar",
                     f"hadoop-aws-{HADOOP_AWS_VER}.jar"]
        jars_str = _get_jars(jar_names)
        delta_conf = _get_delta_lake_conf(jars_str)
        for key, value in delta_conf.items():
            spark_conf.set(key, value)

    return SparkSession.builder.config(conf=spark_conf).enableHiveSupport().getOrCreate()
