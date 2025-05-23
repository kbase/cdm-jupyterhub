#!/bin/bash

if [ "$JUPYTER_MODE" = "jupyterlab" ]; then
  echo "ERROR: jupyterlab mode is no longer supported"
  exit 1
elif [ "$JUPYTER_MODE" = "jupyterhub" ]; then
  echo "starting jupyterhub"
  # unset global $NOTEBOOK_DIR var, as it should be configured individually for each user's spawner
  unset NOTEBOOK_DIR
  # required by jupyterhub in order to enable authentication state
  # ref: https://jupyterhub.readthedocs.io/en/latest/reference/authenticators.html#authentication-state
  export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)
  jupyterhub -f "$JUPYTERHUB_CONFIG_DIR"/jupyterhub_config.py
elif [ "$JUPYTER_MODE" = "jupyterhub-singleuser" ]; then
  echo "Starting Jupyter Notebook for user: $JUPYTERHUB_USER"
  unset NOTEBOOK_DIR

  python /src/jupyterhub_config/hub_singleuser.py

else
  echo "ERROR: JUPYTER_MODE is not set to jupyterlab or jupyterhub. Please set JUPYTER_MODE to either jupyterlab or jupyterhub."
  exit 1
fi