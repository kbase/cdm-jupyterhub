#!/bin/bash

. /opt/scripts/setup.sh

exec /opt/scripts/notebook_entrypoint.sh "$@"