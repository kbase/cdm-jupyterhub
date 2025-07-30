"""
This file handles the importation of essential modules and functions pre-configured for the notebook.

With the PYTHONPATH configured to /src by the Dockerfile, we can directly import modules from the src directory.
"""

from spark.utils import (
    get_spark_session,
    read_csv,
)
from spark.data_store import (
    get_databases,
    get_tables,
    get_table_schema,
    get_db_structure,
)
from db_ops.spark_db_utils import (
    create_namespace_if_not_exists,
    table_exists,
    remove_table,
)
from minio_utils.minio_utils import get_minio_client
from notebook_utils.notebook_utils import (
    display_df,
    spark_to_pandas,
    display_namespace_viewer,
)
from notebook_utils.cts_client import get_task_service_client
from minio_governance.client import DataGovernanceClient
from minio_governance.utils import (
    check_governance_health,
    get_minio_credentials,
    get_my_sql_warehouse,
    get_my_policies,
    get_my_workspace,
    get_path_access_info,
    make_table_private,
    make_table_public,
    share_table,
    unshare_table,
)
from spark.cluster import (
    check_api_health,
    create_cluster,
    delete_cluster,
    get_cluster_status,
)

# Pre-initialize data governance client for easy access
governance = DataGovernanceClient()