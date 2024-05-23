FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc curl unzip\
    && rm -rf /var/lib/apt/lists/*

# Install Gradle
ENV GRADLE_VERSION=8.7
RUN curl -L https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip -o gradle-bin.zip \
    && unzip gradle-bin.zip -d /opt \
    && rm gradle-bin.zip \
    && ln -s /opt/gradle-${GRADLE_VERSION}/bin/gradle /usr/bin/gradle

ENV HADOOP_AWS_VER=3.3.4
# NOTE: ensure Delta Spark jar version matches python pip delta-spark version specified in the Pipfile
ENV DELTA_SPARK_VER=3.2.0
ENV SCALA_VER=2.12

COPY build.gradle /gradle/build.gradle

# Run Gradle task to download JARs to /gradle/gradle_jars location
RUN gradle -b /gradle/build.gradle downloadJars
RUN cp -r /gradle/gradle_jars/* /opt/bitnami/spark/jars/

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
