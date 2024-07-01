#!/bin/bash

# This script sets up the Spark environment variables and configurations for Spark master, worker, and driver (Jupyter) nodes.

# Load Spark environment variables
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

# Config hive-site.xml for Hive support
sed -e "s|{{HIVE_METASTORE_THRIFT_URIS}}|${HIVE_METASTORE_THRIFT_URIS}|g" \
    /opt/config/hive-site-template.xml > "$SPARK_HOME"/conf/hive-site.xml

# Set settings based on server usage
set_environment() {
    local lowercase_usage_mode=${USAGE_MODE,,}  # Convert to lowercase

    case "$lowercase_usage_mode" in
        dev)
            export NOTEBOOK_DIR="$CDM_SHARED_DIR"
            ;;
        *)
            export NOTEBOOK_DIR="$CDM_SHARED_DIR/user_shared_workspace"
            ;;
    esac
    echo "Environment settings applied for $USAGE_MODE."
}

set_environment
