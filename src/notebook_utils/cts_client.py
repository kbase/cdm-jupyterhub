"""
Small helper to create a CDM task service client in a Jupyter notebook.

See:
https://github.com/kbase/cdm-task-service-client/
https://github.com/kbase/cdm-task-service/
https://github.com/kbase/cdm-spark-events
"""

import os

from cdmtaskserviceclient.client import CTSClient

# should probably put this in a common module, it's used in several places
_ENV_AUTH_TOKEN = "KBASE_AUTH_TOKEN"
_ENV_CTS_URL = "CDM_TASK_SERVICE_URL"


def get_task_service_client() -> CTSClient:
    """ Get an instace of the CDM Task Service client. """
    # will throw an error if either env var is undefined
    return CTSClient(os.environ.get(_ENV_AUTH_TOKEN), url=os.environ.get(_ENV_CTS_URL))
