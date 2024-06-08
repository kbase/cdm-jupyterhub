#!/bin/bash

echo "starting jupyter notebook"

cd "$CDM_SHARED_DIR"

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

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 \
            --port="$NOTEBOOK_PORT" \
            --no-browser \
            --allow-root \
            --notebook-dir="$CDM_SHARED_DIR" \
            --ServerApp.token='' \
            --ServerApp.password=''