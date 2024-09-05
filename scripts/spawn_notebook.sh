#!/bin/bash

USERNAME=${JUPYTERHUB_USER}

echo "Starting Jupyter Notebook for user: $USERNAME"
cd $JUPYTERHUB_USER_HOME/$USERNAME

# Start the notebook server with current user
exec jupyterhub-singleuser