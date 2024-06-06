
"""
This file handles the importation of essential modules and functions pre-configured for the notebook.

With the PYTHONPATH configured to /src by the Dockerfile, we can directly import modules from the src directory.
"""

from spark.utils import get_spark_session
from db_ops.spark_db_utils import create_namespace_if_not_exists, table_exists, remove_table
