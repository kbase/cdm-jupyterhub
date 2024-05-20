FROM bitnami/spark:3.5.1

RUN export ORI_USER=$(id -u)
# Switch to root to install packages
USER root

RUN apt-get update && apt-get install -y \
    # GCC required to resolve error during JupyterLab installation: psutil could not be installed from sources because gcc is not installed.
    gcc \
    && rm -rf /var/lib/apt/lists/*

# install pipenv
RUN pip3 install pipenv

# install python dependencies
COPY Pipfile* ./
RUN pipenv sync --system

COPY ./src/ /src
ENV PYTHONPATH "${PYTHONPATH}:/src"

COPY scripts/entrypoint.sh /opt/
RUN chmod a+x /opt/entrypoint.sh

# Switch back to the original user
USER ${ORI_USER}

ENTRYPOINT ["/opt/entrypoint.sh"]
