FROM bitnami/spark:3.5.1

# Switch to root to install packages
# https://github.com/bitnami/containers/tree/main/bitnami/spark#installing-additional-jars
USER root

# Create a non-root user
# User 1001 is not defined in /etc/passwd in the bitnami/spark image, causing various issues.
# References:
# https://github.com/bitnami/containers/issues/52698
# https://github.com/bitnami/containers/pull/52661
RUN groupadd -r spark && useradd -r -g spark spark_user

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc \
    curl \
    git \
    wget \
    vim \
    npm \
    nodejs \
    graphviz \
    graphviz-dev \
    libgdal-dev \
    build-essential \
    python3-dev \
    sudo \
    # tools for troubleshooting network issues
    iputils-ping dnsutils netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

ENV HADOOP_AWS_VER=3.3.4
# NOTE: ensure Delta Spark jar version matches python pip delta-spark version specified in the Pipfile
ENV DELTA_SPARK_VER=3.2.0
ENV SCALA_VER=2.12
ENV POSTGRES_JDBC_VER=42.2.23

# Run Gradle task to download JARs to /gradle/gradle_jars location
COPY build.gradle settings.gradle gradlew /gradle/
COPY gradle /gradle/gradle
ENV GRADLE_JARS_DIR=gradle_jars
RUN /gradle/gradlew -p /gradle build && \
    cp -r /gradle/${GRADLE_JARS_DIR}/* /opt/bitnami/spark/jars/ && \
    rm -rf /gradle

# make an empty yarn conf dir to prevent spark from complaining
RUN mkdir -p /opt/yarn/conf && chown -R spark_user:spark /opt/yarn
ENV YARN_CONF_DIR=/opt/yarn/conf

# Install pipenv and Python dependencies with cache cleanup
RUN pip3 install --no-cache-dir pipenv
COPY Pipfile* ./
RUN pipenv sync --system && pipenv --clear

# This `chown` command modifies the ownership of the entire /opt/bitnami directory to spark_user:spark,
# increasing the image size by 3.6GB. It was previously necessary when using the spark_user user.
# However, since we now operate as the root user, this step is no longer required.
# We are retaining it as commented in case we need to revert to spark_user in the future.
# RUN chown -R spark_user:spark /opt/bitnami

# Set up JupyterLab directories
ENV JUPYTER_CONFIG_DIR=/.jupyter
ENV JUPYTER_RUNTIME_DIR=/.jupyter/runtime
ENV JUPYTER_DATA_DIR=/.jupyter/data
RUN mkdir -p ${JUPYTER_CONFIG_DIR} ${JUPYTER_RUNTIME_DIR} ${JUPYTER_DATA_DIR}
RUN chown -R spark_user:spark /.jupyter

# Set up JupyterHub directories
ENV JUPYTERHUB_CONFIG_DIR=/srv/jupyterhub
RUN mkdir -p ${JUPYTERHUB_CONFIG_DIR}
ENV JUPYTER_AI_CONFIG_FILE=jupyter_jupyter_ai_config.json
COPY ./config/${JUPYTER_AI_CONFIG_FILE} ${JUPYTERHUB_CONFIG_DIR}/${JUPYTER_AI_CONFIG_FILE}
COPY ./src/notebook_utils/startup.py ${JUPYTERHUB_CONFIG_DIR}/startup.py
COPY ./config/jupyterhub_config.py ${JUPYTERHUB_CONFIG_DIR}/jupyterhub_config.py
COPY ./scripts/spawn_notebook.sh ${JUPYTERHUB_CONFIG_DIR}/spawn_notebook.sh
RUN chmod +x ${JUPYTERHUB_CONFIG_DIR}/spawn_notebook.sh
RUN chown -R spark_user:spark ${JUPYTERHUB_CONFIG_DIR}

# Jupyter Hub user home directory
ENV JUPYTERHUB_USER_HOME=/jupyterhub/users_home
RUN mkdir -p $JUPYTERHUB_USER_HOME
RUN chown -R spark_user:spark /jupyterhub

# Jupyter Hub UI templates directory
ENV JUPYTERHUB_TEMPLATES_DIR=/templates
RUN mkdir -p ${JUPYTERHUB_TEMPLATES_DIR}
COPY ./templates/ ${JUPYTERHUB_TEMPLATES_DIR}

RUN npm install -g configurable-http-proxy && npm cache clean --force

COPY ./src/ /src
ENV PYTHONPATH="${PYTHONPATH}:/src"

# Copy the startup script to the default profile location to automatically load pre-built functions in Jupyter Notebook
COPY ./src/notebook_utils/startup.py /.ipython/profile_default/startup/
RUN chown -R spark_user:spark /.ipython

COPY ./scripts/ /opt/scripts/
RUN chmod a+x /opt/scripts/*.sh

# Copy the configuration files
ENV CONFIG_DIR=/opt/config
COPY ./config/ ${CONFIG_DIR}
ENV SPARK_FAIR_SCHEDULER_CONFIG=${CONFIG_DIR}/spark-fairscheduler.xml

# Don't just do /opt since we already did bitnami
RUN chown -R spark_user:spark /src /opt/scripts /opt/config

# This is the shared directory between the spark master, worker and driver containers
ENV CDM_SHARED_DIR=/cdm_shared_workspace
RUN mkdir -p ${CDM_SHARED_DIR} && chmod -R 777 ${CDM_SHARED_DIR}
RUN chown -R spark_user:spark $CDM_SHARED_DIR

# TODO: Config through a config file or DB as the number of groups increases.
ENV KBASE_GROUP_SHARED_DIR=$CDM_SHARED_DIR/kbase_group_shared
RUN mkdir -p ${KBASE_GROUP_SHARED_DIR} && chmod -R 777 ${KBASE_GROUP_SHARED_DIR}
RUN chown -R spark_user:spark $KBASE_GROUP_SHARED_DIR

# Set a directory for hosting Hive metastore files - defined in config/hive-site-template.xml
ENV HIVE_METASTORE_DIR=$CDM_SHARED_DIR/hive_metastore
RUN mkdir -p ${HIVE_METASTORE_DIR}
RUN chown -R spark_user:spark $HIVE_METASTORE_DIR

# Set a directory for hosting Jupyterhub db and cookie secret
ENV JUPYTERHUB_SECRETS_DIR=/jupyterhub_secrets
RUN mkdir -p ${JUPYTERHUB_SECRETS_DIR}
RUN chown -R spark_user:spark ${JUPYTERHUB_SECRETS_DIR}

# Allow spark_user to use sudo without a password
# TODO: use `sudospawner` in JupyterHub to avoid this (https://jupyterhub.readthedocs.io/en/stable/howto/configuration/config-sudo.html)
RUN echo "spark_user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Switch back to non-root user
# Facing permission errors when accessing the Docker API as a non-root user
#USER spark_user


ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
