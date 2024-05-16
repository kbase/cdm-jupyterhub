FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

ENV PYTHON_VER=python3.11

# Install necessary packages
RUN apt-get update && apt-get install -y \
    $PYTHON_VER python3-pip $PYTHON_VER-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Jupyterlab and other python dependencies
RUN pip3 install jupyterlab==4.2.0 pyspark==3.5.1

COPY scripts/entrypoint.sh /opt/
RUN chmod a+x /opt/entrypoint.sh

# Switch back to the original user
#USER ${ORI_USER}

ENTRYPOINT ["/opt/entrypoint.sh"]
