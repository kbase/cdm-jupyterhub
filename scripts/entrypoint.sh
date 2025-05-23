#!/bin/bash

# First run the original setup script defined in the cdm-spark-standalone image
# https://github.com/kbase/cdm-spark-standalone/blob/main/scripts/entrypoint.sh#L3
. /opt/scripts/setup.sh

/opt/scripts/notebook_entrypoint.sh "$@"