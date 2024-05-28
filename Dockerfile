FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc curl unzip\
    && rm -rf /var/lib/apt/lists/*

ENV HADOOP_AWS_VER=3.3.4
# NOTE: ensure Delta Spark jar version matches python pip delta-spark version specified in the Pipfile
ENV DELTA_SPARK_VER=3.2.0
ENV SCALA_VER=2.12

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

COPY ./scripts/ /opt/scripts/
RUN chmod a+x /opt/scripts/*.sh

# Switch back to the original user
USER ${ORI_USER}

ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
