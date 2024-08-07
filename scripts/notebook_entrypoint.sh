#!/bin/bash

echo "starting jupyter notebook"

# Ensure NOTEBOOK_DIR is set
if [ -z "$NOTEBOOK_DIR" ]; then
    echo "ERROR: NOTEBOOK_DIR is not set. Please run setup.sh first."
    exit 1
fi

mkdir -p "$NOTEBOOK_DIR" && cd "$NOTEBOOK_DIR"

# Enable SparkMonitor extension
# https://github.com/swan-cern/sparkmonitor?tab=readme-ov-file#setting-up-the-extension
enable_spark_monitor() {
    echo "Enabling SparkMonitor extension..."
    local ipython_config_path="/.ipython/profile_default/ipython_kernel_config.py"
    local spark_monitor_config="c.InteractiveShellApp.extensions.append('sparkmonitor.kernelextension')"

    if ! grep -q "$spark_monitor_config" "$ipython_config_path"; then
        echo "$spark_monitor_config" >> "$ipython_config_path"
        echo "SparkMonitor kernel extension enabled in IPython config."
    else
        echo "SparkMonitor kernel extension is already enabled in IPython config."
    fi
}

enable_spark_monitor

# install Plotly extension
jupyter labextension install jupyterlab-plotly@5.23.0

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$NOTEBOOK_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''