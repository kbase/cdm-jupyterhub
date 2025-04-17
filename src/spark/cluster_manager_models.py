"""
Pydantic models for the Spark Manager API.
"""

# copied from https://github.com/kbase/cdm-kube-spark-manager/blob/main/src/service/models.py

from typing import Annotated

from pydantic import BaseModel, ByteSize, Field

GiB = 1024 * 1024 * 1024
MIN_MEMORY_BYTES = int(0.1 * GiB)  # 100MB
MAX_MEMORY_BYTES = 256 * GiB  # 256GB

MAX_WORKER_COUNT = 25
MAX_WORKER_CORES = 64
MAX_MASTER_CORES = 64

DEFAULT_WORKER_COUNT = 2
DEFAULT_WORKER_CORES = 10
DEFAULT_WORKER_MEMORY = "10GiB"
DEFAULT_MASTER_CORES = 10
DEFAULT_MASTER_MEMORY = "10GiB"


class SparkClusterConfig(BaseModel):
    """Configuration for creating a new Spark cluster."""

    worker_count: Annotated[
        int,
        Field(
            description=f"Number of worker nodes in the Spark cluster (Range: 1 to {MAX_WORKER_COUNT}).",
            ge=1,
            le=MAX_WORKER_COUNT,
            examples=[DEFAULT_WORKER_COUNT, 10],
            default=DEFAULT_WORKER_COUNT,
        ),
    ] = DEFAULT_WORKER_COUNT

    worker_cores: Annotated[
        int,
        Field(
            description=f"Number of CPU cores allocated to each worker node (Range: 1 to {MAX_WORKER_CORES}).",
            ge=1,
            le=MAX_WORKER_CORES,
            examples=[DEFAULT_WORKER_CORES, 16],
            default=DEFAULT_WORKER_CORES,
        ),
    ] = DEFAULT_WORKER_CORES

    worker_memory: Annotated[
        ByteSize,
        Field(
            description=f"Memory allocated per worker node (Range: {MIN_MEMORY_BYTES / (1024*1024):.1f} MiB to {MAX_MEMORY_BYTES / GiB:.0f} GiB). Accepts formats like '10GiB', '10240MiB'.",
            ge=MIN_MEMORY_BYTES,
            le=MAX_MEMORY_BYTES,
            examples=[DEFAULT_WORKER_MEMORY, "32GiB"],
            default=DEFAULT_WORKER_MEMORY,
        ),
    ] = DEFAULT_WORKER_MEMORY  # type: ignore[assignment] - Pydantic handles the string -> ByteSize conversion during validation/initialization.

    master_cores: Annotated[
        int,
        Field(
            description=f"Number of CPU cores allocated to the master node (Range: 1 to {MAX_MASTER_CORES}).",
            ge=1,
            le=MAX_MASTER_CORES,
            examples=[DEFAULT_MASTER_CORES, 8],
            default=DEFAULT_MASTER_CORES,
        ),
    ] = DEFAULT_MASTER_CORES

    master_memory: Annotated[
        ByteSize,
        Field(
            description=f"Memory allocated for the master node (Range: {MIN_MEMORY_BYTES / (1024*1024):.1f} MiB to {MAX_MEMORY_BYTES / GiB:.0f} GiB). Accepts formats like '10GiB', '10240MiB'.",
            ge=MIN_MEMORY_BYTES,
            le=MAX_MEMORY_BYTES,
            examples=[DEFAULT_MASTER_MEMORY, "16GiB"],
            default=DEFAULT_MASTER_MEMORY,
        ),
    ] = DEFAULT_MASTER_MEMORY  # type: ignore[assignment] - Pydantic handles the string -> ByteSize conversion during validation/initialization.


class SparkClusterCreateResponse(BaseModel):
    """Response model for cluster creation."""

    cluster_id: Annotated[str, Field(description="Unique identifier for the cluster")]
    master_url: Annotated[str, Field(description="URL to connect to the Spark master")]
    master_ui_url: Annotated[
        str, Field(description="URL to access the Spark master UI")
    ]


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: Annotated[int | None, Field(description="Error code")] = None
    error_type: Annotated[str | None, Field(description="Error type")] = None
    message: Annotated[str | None, Field(description="Error message")] = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Annotated[str, Field(description="Health status")]


class DeploymentStatus(BaseModel):
    """Status information of a Kubernetes deployment."""

    available_replicas: Annotated[
        int, Field(description="Number of available replicas")
    ] = 0
    ready_replicas: Annotated[int, Field(description="Number of ready replicas")] = 0
    replicas: Annotated[int, Field(description="Total number of desired replicas")] = 0
    unavailable_replicas: Annotated[
        int, Field(description="Number of unavailable replicas")
    ] = 0
    is_ready: Annotated[bool, Field(description="Whether all replicas are ready")] = (
        False
    )
    exists: Annotated[bool, Field(description="Whether the deployment exists")] = True
    error: Annotated[str | None, Field(description="Error message if any")] = None


class SparkClusterStatus(BaseModel):
    """Status information about a Spark cluster."""

    master: Annotated[DeploymentStatus, Field(description="Master node status")]
    workers: Annotated[DeploymentStatus, Field(description="Worker nodes status")]
    master_url: Annotated[str | None, Field(description="Spark master URL")] = None
    master_ui_url: Annotated[str | None, Field(description="Spark master UI URL")] = (
        None
    )
    error: Annotated[
        bool, Field(description="Whether there was an error during the status check")
    ] = False


class ClusterDeleteResponse(BaseModel):
    """Response model for cluster deletion."""

    message: Annotated[str, Field(description="Success deletion message")]