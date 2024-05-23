import os

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession


def get_spark_session(app_name: str,
                      local: bool = False,
                      delta_lake: bool = False) -> SparkSession:
    """
    Helper to get and manage the `SparkSession` and keep all of our spark configuration params in one place.

    :param app_name: The name of the application
    :param local: Whether to run the spark session locally or doesn't
    :param delta_lake: build the spark session with delta lake support

    :return: A `SparkSession` object
    """

    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    spark_conf = SparkConf()

    if delta_lake:

        jars_dir = "/opt/bitnami/spark/jars/"
        jar_files = [os.path.join(jars_dir, f) for f in os.listdir(jars_dir) if f.endswith(".jar")]
        jars = ",".join(jar_files)

        spark_conf.setAll(
            [
                (
                    "spark.master",
                    os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077"),
                ),
                ("spark.app.name", app_name),
                ("spark.hadoop.fs.s3a.endpoint", os.environ.get("MINIO_URL")),
                ("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ACCESS_KEY")),
                ("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_SECRET_KEY")),
                ("spark.jars", jars),
                ("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension"),
                ("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"),
                ("spark.hadoop.fs.s3a.path.style.access", "true"),
                ("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem"),
            ]
        )
    else:
        spark_conf.setAll(
            [
                (
                    "spark.master",
                    os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077"),
                ),
                ("spark.app.name", app_name),
            ]
        )

    return SparkSession.builder.config(conf=spark_conf).getOrCreate()
