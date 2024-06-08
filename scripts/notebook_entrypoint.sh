#!/bin/bash

echo "starting jupyter notebook"

lowercase_usage_mode=${USAGE_MODE,,}

case "$lowercase_usage_mode" in
    dev)
        export NOTEBOOK_DIR="$CDM_SHARED_DIR"
        ;;
    *)
        export NOTEBOOK_DIR="$CDM_SHARED_DIR/user_shared_workspace"
        ;;
esac

mkdir -p "$NOTEBOOK_DIR" && cd "$NOTEBOOK_DIR"

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$NOTEBOOK_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''