import logging
import os
import uuid
from typing import Dict, List, Optional

import kubernetes as k8s

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KubeSparkManager:
    """
    Manager for user-specific Spark clusters in Kubernetes.
    
    This class provides methods to create, manage, and destroy Spark clusters
    for individual JupyterHub users.
    """

    # Required environment variables
    REQUIRED_ENV_VARS = {
        "KUBE_NAMESPACE": "Kubernetes namespace for Spark clusters",
        "SPARK_IMAGE": "Docker image for Spark master and workers",
        "POSTGRES_USER": "PostgreSQL username",
        "POSTGRES_PASSWORD": "PostgreSQL password",
        "POSTGRES_DB": "PostgreSQL database name",
        "POSTGRES_URL": "PostgreSQL connection URL"
    }

    # Default configuration values for cluster settings
    DEFAULT_WORKER_COUNT = 2
    DEFAULT_WORKER_CORES = 10
    DEFAULT_WORKER_MEMORY = "10G"
    DEFAULT_MASTER_CORES = 10
    DEFAULT_MASTER_MEMORY = "10G"

    DEFAULT_IMAGE_PULL_POLICY = os.environ.get("SPARK_IMAGE_PULL_POLICY", "IfNotPresent")

    DEFAULT_EXECUTOR_CORES = 2
    DEFAULT_MAX_CORES_PER_APPLICATION = 10
    DEFAULT_MAX_EXECUTORS = 5

    DEFAULT_MASTER_PORT = 7077
    DEFAULT_MASTER_WEBUI_PORT = 8090
    DEFAULT_WORKER_WEBUI_PORT = 8081

    @classmethod
    def validate_environment(cls) -> Dict[str, str]:
        """
        Validate that all required environment variables are set.

        Returns:
            Dict[str, str]: Dictionary of validated environment variables
        """
        missing_vars = []
        env_values = {}

        for var, description in cls.REQUIRED_ENV_VARS.items():
            value = os.environ.get(var)
            if not value or not value.strip():
                missing_vars.append(f"{var} ({description})")
            env_values[var] = value

        if missing_vars:
            raise ValueError(
                "Missing required environment variables:\n" +
                "\n".join(f"- {var}" for var in missing_vars)
            )

        return env_values

    def __init__(self,
                 username: str,
                 namespace: Optional[str] = None,
                 image: Optional[str] = None,
                 image_pull_policy: str = DEFAULT_IMAGE_PULL_POLICY):
        """
        Initialize the KubeSparkManager with user-specific configuration.

        Args:
            username: Username of the JupyterHub user
            namespace: Optional override for Kubernetes namespace
            image: Optional override for Docker image
            image_pull_policy: Optional override for image pull policy

        Raises:
            ValueError: If required environment variables are not set
        """
        # Validate environment variables
        env_vars = self.validate_environment()

        self.username = username
        self.namespace = namespace or env_vars["KUBE_NAMESPACE"]
        self.image = image or env_vars["SPARK_IMAGE"]
        self.image_pull_policy = image_pull_policy

        # Generate a unique identifier for this user's Spark cluster
        self.cluster_id = f"spark-{username.lower()}-{str(uuid.uuid4())[:8]}"

        # Service names
        self.master_name = f"spark-master-{username.lower()}"
        self.worker_name = f"spark-worker-{username.lower()}"

        # Initialize Kubernetes client
        k8s.config.load_incluster_config()
        self.core_api = k8s.client.CoreV1Api()
        self.apps_api = k8s.client.AppsV1Api()

        logger.info(f"Initialized KubeSparkManager for user {username} in namespace {namespace}")

    def create_cluster(self,
                       worker_count: int = DEFAULT_WORKER_COUNT,
                       worker_cores: int = DEFAULT_WORKER_CORES,
                       worker_memory: str = DEFAULT_WORKER_MEMORY,
                       master_cores: int = DEFAULT_MASTER_CORES,
                       master_memory: str = DEFAULT_MASTER_MEMORY) -> str:
        """
        Create a new Spark cluster for the user.
        
        Args:
            worker_count: Number of Spark worker replicas
            worker_cores: Number of CPU cores for each worker
            worker_memory: Memory allocation for each worker
            master_cores: Number of CPU cores for the master
            master_memory: Memory allocation for the master
            
        Returns:
            The Spark master URL for connecting to the cluster
        """
        # Create or validate postgres config
        postgres_env = self._prepare_postgres_config()

        # TODO: Create the Spark master deployment and service
        # TODO: Create the Spark worker deployment and service

        # Return the Spark master URL
        master_url = f"spark://{self.master_name}.{self.namespace}:{self.DEFAULT_MASTER_PORT}"

        logger.info(f"Created Spark cluster for user {self.username} with master URL: {master_url}")
        return master_url

    @staticmethod
    def _prepare_postgres_config() -> List[Dict[str, str]]:
        """
        Prepare Postgres environment variables for Hive metastore.

        """

        # Postgres configuration from environment variables
        postgres_config = {
            "POSTGRES_USER": os.environ["POSTGRES_USER"],
            "POSTGRES_PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "POSTGRES_DB": os.environ["POSTGRES_DB"],
            "POSTGRES_URL": os.environ["POSTGRES_URL"]
        }

        # Convert to Kubernetes env var format
        return [{"name": k, "value": v} for k, v in postgres_config.items()]


