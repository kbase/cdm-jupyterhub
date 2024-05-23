#!/bin/bash

if [ "$SPARK_MODE" = "notebook" ]; then
    exec /opt/scripts/notebook_entrypoint.sh "$@"
else
  # In bitnami/spark Dockerfile, the entrypoint is set to /opt/bitnami/scripts/spark/entrypoint.sh and followed
  # by CMD ["/opt/bitnami/scripts/spark/run.sh"] meaning that the entrypoint is expected the run.sh script as an argument.
  # reference: https://github.com/bitnami/containers/blob/main/bitnami/spark/3.5/debian-12/Dockerfile#L69
    exec /opt/bitnami/scripts/spark/entrypoint.sh "$@" /opt/bitnami/scripts/spark/run.sh
fi