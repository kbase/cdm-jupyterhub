#!/bin/bash

echo "starting jupyter notebook"

if [ -n "$SPARK_DRIVER_HOST" ]; then
    echo "Setting spark.driver.host to $SPARK_DRIVER_HOST"
    source /opt/bitnami/scripts/spark-env.sh
    if [ -z "$SPARK_CONF_FILE" ]; then
        echo "Error: unable to find SPARK_CONF_FILE path"
        exit 1
    fi
    echo "spark.driver.host $SPARK_DRIVER_HOST" >> $SPARK_CONF_FILE
fi

WORKSPACE_DIR="/cdm_shared_workspace"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port=$NOTEBOOK_PORT \
            --no-browser \
            --allow-root \
            --notebook-dir="$WORKSPACE_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''