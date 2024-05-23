#!/bin/bash

if [ "$SPARK_MODE" = "notebook" ]; then
    exec /opt/scripts/notebook_entrypoint.sh "$@"
else
    exec /opt/bitnami/scripts/spark/entrypoint.sh "$@"
fi