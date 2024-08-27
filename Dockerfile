# Stage 1: Build and Install Dependencies
FROM bitnami/spark:3.5.1 AS build-stage

# Switch to root to install packages
USER root

# Create a non-root user
RUN groupadd -r spark && useradd -r -g spark spark_user

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    gcc curl git graphviz graphviz-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for tools and libraries
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

# Set up Jupyter directories
RUN mkdir -p /.jupyter /.jupyter/runtime /.jupyter/data

# Copy application source and configuration files
COPY ./src/ /src
COPY ./config/ /opt/config/
COPY ./scripts/ /opt/scripts/

# Stage 2: Final Image (Slimmed Down)
FROM bitnami/spark:3.5.1 AS runtime-stage

# Switch to root to set up the environment
USER root

# Create the same non-root user
RUN groupadd -r spark && useradd -r -g spark spark_user

# Copy only necessary files from the build stage
COPY --from=build-stage /opt/bitnami/spark/jars/ /opt/bitnami/spark/jars/

# Copy Python packages from the correct path
COPY --from=build-stage /opt/bitnami/python/lib/python3.11/site-packages/ /opt/bitnami/python/lib/python3.11/site-packages/

# Copy pipenv from the correct path
COPY --from=build-stage /opt/bitnami/python/bin/pipenv /opt/bitnami/python/bin/pipenv

# Continue copying the rest of the necessary files
COPY --from=build-stage /src /src
COPY --from=build-stage /opt/config/ /opt/config/
COPY --from=build-stage /opt/scripts/ /opt/scripts/

# Set up Jupyter directories
COPY --from=build-stage /.jupyter /.jupyter

# Set correct ownership and permissions
RUN chown -R spark_user:spark /opt/bitnami /src /opt/scripts /opt/config /.jupyter
RUN chmod +x /opt/scripts/entrypoint.sh
RUN ln -s /opt/scripts/entrypoint.sh /entrypoint.sh

# Set up shared directory between Spark components
ENV CDM_SHARED_DIR=/cdm_shared_workspace
RUN mkdir -p ${CDM_SHARED_DIR} && chmod -R 777 ${CDM_SHARED_DIR}
RUN chown -R spark_user:spark $CDM_SHARED_DIR

# Switch back to non-root user
USER spark_user

# Entry point for the container
# ENTRYPOINT ["/opt/scripts/entrypoint.sh"]

