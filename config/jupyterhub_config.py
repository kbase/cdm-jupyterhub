"""
This is the JupyterHub configuration file. It is used to configure the JupyterHub server.
Refer to the JupyterHub documentation for more information:
https://jupyterhub.readthedocs.io/en/latest/tutorial/getting-started/config-basics.html
https://jupyterhub.readthedocs.io/en/stable/reference/config-reference.html
"""
import os

from jupyterhub_config.custom_spawner import VirtualEnvSpawner

c = get_config()

# Set the authenticator class
# TODO: Change the authenticator class to a secure one (e.g. GitHubOAuthenticator)
c.JupyterHub.authenticator_class = 'jupyterhub.auth.DummyAuthenticator'
c.Authenticator.allowed_users = {'spark_user', 'test_user1', 'test_user2'}
c.DummyAuthenticator.password = os.environ['JUPYTERHUB_ADMIN_PASSWORD']

c.Authenticator.admin_users = {'spark_user'}

c.JupyterHub.spawner_class = VirtualEnvSpawner

# Set the JupyterHub IP address and port
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = int(os.getenv('NOTEBOOK_PORT'))

c.JupyterHub.log_level = 'DEBUG'