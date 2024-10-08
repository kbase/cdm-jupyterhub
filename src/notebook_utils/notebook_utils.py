from threading import RLock

import itables.options as opt
import pandas as pd
from ipywidgets import Accordion, VBox, HTML
from itables import init_notebook_mode, show
from pandas import DataFrame as PandasDataFrame
from pyspark.sql import DataFrame as SparkDataFrame, SparkSession

lock = RLock()


def spark_to_pandas(
        spark_df: SparkDataFrame,
        limit: int = 1000,
        offset: int = 0
) -> PandasDataFrame:
    """
    Convert a Spark DataFrame to a pandas DataFrame.

    :param spark_df: a Spark DataFrame
    :param limit: the number of rows to fetch
    :param offset: the number of rows to skip
    :return: a pandas DataFrame
    """

    return spark_df.offset(offset).limit(limit).toPandas()


def display_df(
        df: PandasDataFrame | SparkDataFrame,
        layout: dict = None,
        buttons: list = None,
        length_menu: list = None
) -> None:
    """
    Display a pandas DataFrame using itables.
    iTables project page: https://github.com/mwouts/itables

    Notice itables.show() function is not compatible with Spark DataFrames. If a Spark DataFrame is passed to this
    function, it will be converted to a pandas DataFrame (first 1000 rows) before displaying it.

    :param df: a pandas DataFrame or a Spark DataFrame
    :param layout: layout options, refer to https://datatables.net/reference/option/layout
    :param buttons: buttons options, options refer to https://datatables.net/reference/button/
    :param length_menu: length menu options, refer to https://datatables.net/reference/option/lengthMenu
    :return:
    """
    # convert Spark DataFrame to pandas DataFrame
    if isinstance(df, SparkDataFrame):
        if df.count() > 1000:
            print("Converting first 1000 rows from Spark to Pandas DataFrame...")
        df = spark_to_pandas(df)

    # initialize itables for the notebook
    init_notebook_mode(all_interactive=False)

    # set default values if options are not provided
    default_layout = {
        "topStart": "search",
        "topEnd": "buttons",
        "bottomStart": "pageLength",
        "bottomEnd": "paging",
        "bottom2Start": "info"
    }
    default_buttons = ["csvHtml5", "excelHtml5", "print"]
    default_length_menu = [5, 10, 20]

    layout = layout or default_layout
    buttons = buttons or default_buttons
    length_menu = length_menu or default_length_menu

    with lock:
        opt.layout = layout
        show(df, buttons=buttons, lengthMenu=length_menu)


def _fetch_namespaces(spark: SparkSession) -> list:
    """
    Retrieve all database namespaces using an active Spark session.
    """
    return spark.sql("SHOW DATABASES").collect()


def _fetch_tables_for_namespace(spark: SparkSession, namespace: str) -> pd.DataFrame:
    """
    Retrieve all tables for a given namespace.
    """
    return spark.sql(f"SHOW TABLES IN {namespace}").toPandas()


def _create_namespace_accordion(spark: SparkSession, namespaces: list) -> Accordion:
    """
    Create an Accordion widget displaying namespaces and their tables.

    ref: https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20List.html#accordion
    """
    accordion = Accordion()
    children_list = []

    for namespace in namespaces:
        namespace_name = namespace.namespace
        tables_df = _fetch_tables_for_namespace(spark, namespace_name)

        table_content = '<br>'.join(tables_df['tableName']) if not tables_df.empty else "No tables available"
        table_list = HTML(value=table_content)

        namespace_section = VBox([table_list])
        children_list.append(namespace_section)

        accordion.children = tuple(children_list)
        accordion.set_title(len(accordion.children) - 1, f"Namespace: {namespace_name}")

    return accordion
