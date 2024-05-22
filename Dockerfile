FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install jars to support delta lake spark operations
ENV HADOOP_AWS_VER=3.3.4
RUN curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VER}/hadoop-aws-${HADOOP_AWS_VER}.jar \
    && mv hadoop-aws-${HADOOP_AWS_VER}.jar /opt/bitnami/spark/jars

# NOTE: ensure Delta Spark jars matche python pip delta-spark version specified in the Pipfile
ENV DELTA_SPARK_VER=3.2.0
ENV SCALA_VER=2.12
RUN curl -O https://repo1.maven.org/maven2/io/delta/delta-spark_${SCALA_VER}/${DELTA_SPARK_VER}/delta-spark_${SCALA_VER}-${DELTA_SPARK_VER}.jar \
    && mv delta-spark_${SCALA_VER}-${DELTA_SPARK_VER}.jar /opt/bitnami/spark/jars

RUN curl -O https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_SPARK_VER}/delta-storage-${DELTA_SPARK_VER}.jar \
    && mv delta-storage-${DELTA_SPARK_VER}.jar /opt/bitnami/spark/jars

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
