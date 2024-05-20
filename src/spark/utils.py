import os

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession


def get_spark_session(app_name: str, local: bool = False) -> SparkSession:
    """
    Helper to get and manage the `SparkSession` and keep all of our spark configuration params in one place.

    :param app_name: The name of the application
    :param local: Whether to run the spark session locally or not

    :return: A `SparkSession` object
    """

    if local:
        return SparkSession.builder.appName(app_name).getOrCreate()

    spark_conf = SparkConf()

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
