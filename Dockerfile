FROM bitnami/spark:3.5.1

# Switch to root to install packages
# https://github.com/bitnami/containers/tree/main/bitnami/spark#installing-additional-jars
USER root

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc curl git \
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
RUN /gradle/gradlew -p /gradle build
RUN cp -r /gradle/${GRADLE_JARS_DIR}/* /opt/bitnami/spark/jars/

# install pipenv
RUN pip3 install pipenv

# install python dependencies
COPY Pipfile* ./
RUN pipenv sync --system

COPY ./src/ /src
ENV PYTHONPATH "${PYTHONPATH}:/src"

# Copy the startup script to the default profile location to automatically load pre-built functions in Jupyter Notebook
COPY ./src/notebook_utils/startup.py /.ipython/profile_default/startup/

COPY ./scripts/ /opt/scripts/
RUN chmod a+x /opt/scripts/*.sh

# Copy the configuration files
COPY ./config/ /opt/config/

# This is the shared directory between the spark master, worker and driver containers
ENV CDM_SHARED_DIR=/cdm_shared_workspace
RUN mkdir -p ${CDM_SHARED_DIR} && chmod -R 777 ${CDM_SHARED_DIR}

# TODO: Switch back to non-root user
#USER 1001

ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
