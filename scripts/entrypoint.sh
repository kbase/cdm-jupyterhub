#!/bin/bash

echo "starting jupyter notebook"

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