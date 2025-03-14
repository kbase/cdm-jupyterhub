#!/bin/bash

# This script sets up the Spark environment variables and configurations for Spark master, worker, and driver (Jupyter) nodes.

# Config hive-site.xml for Hive support
sed -e "s|{{POSTGRES_URL}}|${POSTGRES_URL}|g" \
    -e "s|{{POSTGRES_DB}}|${POSTGRES_DB}|g" \
    -e "s|{{POSTGRES_USER}}|${POSTGRES_USER}|g" \
    -e "s|{{POSTGRES_PASSWORD}}|${POSTGRES_PASSWORD}|g" \
    /opt/config/hive-site-template.xml > "$SPARK_HOME"/conf/hive-site.xml


update_config() {
    sed -i "s|{{DATANUCLEUS_AUTO_CREATE_TABLES}}|${DATANUCLEUS_AUTO_CREATE_TABLES}|g" "$SPARK_HOME"/conf/hive-site.xml
}

# Set settings based on server usage
set_environment() {
    local lowercase_usage_mode=${USAGE_MODE,,}  # Convert to lowercase

    case "$lowercase_usage_mode" in
        dev)
            export DATANUCLEUS_AUTO_CREATE_TABLES=true
            export NOTEBOOK_DIR="$CDM_SHARED_DIR"
            ;;
        *)
            export DATANUCLEUS_AUTO_CREATE_TABLES=false
            export NOTEBOOK_DIR="$CDM_SHARED_DIR/user_shared_workspace"
            ;;
    esac
    update_config
    echo "Environment settings applied for $USAGE_MODE."
}

set_environment