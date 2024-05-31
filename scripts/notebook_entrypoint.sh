#!/bin/bash

echo "starting jupyter notebook"

source /opt/bitnami/scripts/spark-env.sh
if [ -z "$SPARK_CONF_FILE" ]; then
    echo "Error: unable to find SPARK_CONF_FILE path"
    exit 1
fi

# Set Spark configurations
{
    # Set dynamic allocation configurations to allow parallel job executions
    if [ -z "$MAX_EXECUTORS" ]; then
      # If MAX_EXECUTORS is not set, default to 5. Adjust as needed.
      MAX_EXECUTORS=5
    fi
    echo "spark.dynamicAllocation.enabled true"
    echo "spark.dynamicAllocation.minExecutors 1"
    echo "spark.dynamicAllocation.maxExecutors $MAX_EXECUTORS"

    # Set spark.driver.host if SPARK_DRIVER_HOST is set
    if [ -n "$SPARK_DRIVER_HOST" ]; then
        echo "spark.driver.host $SPARK_DRIVER_HOST"
    fi
} >> "$SPARK_CONF_FILE"

WORKSPACE_DIR="/cdm_shared_workspace"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$WORKSPACE_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''