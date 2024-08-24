# Base image for building dependencies
FROM bitnami/spark:3.5.1 AS build-stage

# Switch to root to install packages
USER root

# Create a non-root user
RUN groupadd -r spark && useradd -r -g spark spark_user

# Install necessary build tools
RUN apt-get update && apt-get install -y \
    gcc curl git graphviz graphviz-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables
ENV HADOOP_AWS_VER=3.3.4
ENV DELTA_SPARK_VER=3.2.0
ENV SCALA_VER=2.12
ENV POSTGRES_JDBC_VER=42.2.23

# Copy build files and run Gradle to download JARs
COPY build.gradle settings.gradle gradlew /gradle/
COPY gradle /gradle/gradle
ENV GRADLE_JARS_DIR=gradle_jars
RUN /gradle/gradlew -p /gradle build

# Install pipenv and Python dependencies
RUN pip3 install pipenv
COPY Pipfile* ./
RUN pipenv sync --system

# Copy necessary files for the final stage
COPY ./src/ /src
COPY ./scripts/ /opt/scripts/
COPY ./config/ /opt/config/

# Create the runtime stage, based on the same image but without the build tools
FROM bitnami/spark:3.5.1 AS runtime-stage

# Switch to root to copy files and set permissions
USER root

# Create the same non-root user as in the build stage
RUN groupadd -r spark && useradd -r -g spark spark_user

# Copy pre-built JARs from the build stage
COPY --from=build-stage /gradle/gradle_jars/* /opt/bitnami/spark/jars/

# Copy Python environment and installed packages
COPY --from=build-stage /usr/local/lib/python3.*/dist-packages /usr/local/lib/python3.*/dist-packages
COPY --from=build-stage /usr/local/bin/pipenv /usr/local/bin/pipenv

# Copy application code, scripts, and config files
COPY --from=build-stage /src /src
COPY --from=build-stage /opt/scripts /opt/scripts
COPY --from=build-stage /opt/config /opt/config

# Make an empty yarn conf dir to prevent spark from complaining
RUN mkdir -p /opt/yarn/conf && chown -R spark_user:spark /opt/yarn
ENV YARN_CONF_DIR=/opt/yarn/conf

# Set up Jupyter directories
ENV JUPYTER_CONFIG_DIR=/.jupyter
ENV JUPYTER_RUNTIME_DIR=/.jupyter/runtime
ENV JUPYTER_DATA_DIR=/.jupyter/data
RUN mkdir -p ${JUPYTER_CONFIG_DIR} ${JUPYTER_RUNTIME_DIR} ${JUPYTER_DATA_DIR}
RUN chown -R spark_user:spark /.jupyter

# Set PYTHONPATH and other environment variables
ENV PYTHONPATH "${PYTHONPATH}:/src"

# Copy the startup script to the default profile location to automatically load pre-built functions in Jupyter Notebook
COPY --from=build-stage /src/notebook_utils/startup.py /.ipython/profile_default/startup/
RUN chown -R spark_user:spark /.ipython

# Set up the shared directory between Spark components
ENV CDM_SHARED_DIR=/cdm_shared_workspace
RUN mkdir -p ${CDM_SHARED_DIR} && chmod -R 777 ${CDM_SHARED_DIR}
RUN chown -R spark_user:spark $CDM_SHARED_DIR

# Set correct permissions for non-root user
RUN chown -R spark_user:spark /opt/bitnami /src /opt/scripts /opt/config

# Switch back to non-root user
USER spark_user

ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
