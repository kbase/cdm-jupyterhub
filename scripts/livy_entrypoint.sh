#!/bin/bash

echo "Starting Livy server..."

# Set Livy configurations
{
    echo "livy.server.host = ${LIVY_SERVER_HOST}"
    echo "livy.server.port = ${LIVY_PORT}"
    echo "livy.spark.master = ${SPARK_MASTER_URL}"
    echo "livy.spark.deploy-mode = client"
    echo "livy.server.session.timeout-check = true"
    echo "livy.server.session.timeout-check.skip-busy = false"
    echo "livy.server.session.timeout = 1h"
#    echo "livy.server.session.state-retain.sec = 60s"
    echo "livy.repl.jars = $(cat "${LIVY_HOME}"/repl_jars.txt)"
} >> "${LIVY_HOME}"/conf/livy.conf

{
    echo "livy.rsc.rpc.server.address = ${LIVY_RSC_RPC_SERVER_ADDRESS}"
} >> "${LIVY_HOME}"/conf/livy-client.conf

{
    echo "export SPARK_HOME=${SPARK_HOME}"
} >> "${LIVY_HOME}"/conf/livy-env.sh

"${LIVY_HOME}"/bin/livy-server
