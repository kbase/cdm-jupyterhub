#!/bin/bash

if [ "$JUPYTER_MODE" = "jupyterlab" ]; then
  echo "starting jupyterlab"

  # Ensure NOTEBOOK_DIR is set
  if [ -z "$NOTEBOOK_DIR" ]; then
      echo "ERROR: NOTEBOOK_DIR is not set. Please run setup.sh first."
      exit 1
  fi

  mkdir -p "$NOTEBOOK_DIR" && cd "$NOTEBOOK_DIR"

  # install Plotly extension
  jupyter labextension install jupyterlab-plotly@5.23.0

  # install ipywidgets extension
  jupyter labextension install @jupyter-widgets/jupyterlab-manager@8.1.3

  # Start Jupyter Lab
  jupyter lab --ip=0.0.0.0 \
              --port="$NOTEBOOK_PORT" \
              --no-browser \
              --allow-root \
              --notebook-dir="$NOTEBOOK_DIR" \
              --ServerApp.token='' \
              --ServerApp.password=''
elif [ "$JUPYTER_MODE" = "jupyterhub" ]; then
  echo "starting jupyterhub"
  # unset global $NOTEBOOK_DIR var, as it should be configured individually for each user's spawner
  unset NOTEBOOK_DIR

  jupyterhub -f "$JUPYTERHUB_CONFIG_DIR"/jupyterhub_config.py
elif [ "$JUPYTER_MODE" = "jupyterhub-singleuser" ]; then
  echo "Starting Jupyter Notebook for user: $JUPYTERHUB_USER"
  unset NOTEBOOK_DIR

  python /src/jupyterhub_config/hub_singleuser.py

else
  echo "ERROR: JUPYTER_MODE is not set to jupyterlab or jupyterhub. Please set JUPYTER_MODE to either jupyterlab or jupyterhub."
  exit 1
fi