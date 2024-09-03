#!/bin/bash

echo "starting jupyter notebook"

# Ensure NOTEBOOK_DIR is set
if [ -z "$NOTEBOOK_DIR" ]; then
    echo "ERROR: NOTEBOOK_DIR is not set. Please run setup.sh first."
    exit 1
fi

mkdir -p "$NOTEBOOK_DIR" && cd "$NOTEBOOK_DIR"

# install Plotly extension
jupyter labextension install jupyterlab-plotly@5.23.0

# install ipywidgets extension
jupyter labextension install @jupyter-widgets/jupyterlab-manager@8.1.3

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$NOTEBOOK_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''