FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

# Install necessary packages
RUN apt-get update && apt-get install -y \
    # Fixing error: psutil could not be installed from sources because gcc is not installed
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Jupyterlab and other python dependencies
RUN pip install jupyterlab==4.2.0 pyspark==3.5.1

COPY scripts/entrypoint.sh /opt/
RUN chmod a+x /opt/entrypoint.sh

# Switch back to the original user
USER ${ORI_USER}

ENTRYPOINT ["/opt/entrypoint.sh"]
