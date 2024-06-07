#!/bin/bash

echo "starting jupyter notebook"

cd "$CDM_SHARED_DIR"

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$CDM_SHARED_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''