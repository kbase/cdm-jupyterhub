"""
This is the JupyterHub configuration file. It is used to configure the JupyterHub server.
Refer to the JupyterHub documentation for more information:
https://jupyterhub.readthedocs.io/en/latest/tutorial/getting-started/config-basics.html
https://jupyterhub.readthedocs.io/en/stable/reference/config-reference.html
"""

import os

import nativeauthenticator

from jupyterhub_config.custom_spawner import VirtualEnvSpawner

c = get_config()

# Set the authenticator class to nativeauthenticator
# ref: https://native-authenticator.readthedocs.io/en/latest/quickstart.html
c.JupyterHub.authenticator_class = 'native'
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]
# ref: https://native-authenticator.readthedocs.io/en/latest/options.html
c.NativeAuthenticator.open_signup = True
c.NativeAuthenticator.check_common_password = True
c.NativeAuthenticator.minimum_password_length = 8

# Set up the admin user
admin_user = 'spark_user'
c.Authenticator.admin_users = {admin_user}
# TODO set admin user password to os.environ['JUPYTERHUB_ADMIN_PASSWORD'] automatically - currently spark_user is created manually with the signup page
# Allow user who can successfully authenticate to access the JupyterHub server
# ref: https://jupyterhub.readthedocs.io/en/latest/reference/api/auth.html#jupyterhub.auth.Authenticator.allow_all
c.Authenticator.allow_all = True

c.JupyterHub.cookie_secret_file = f"{os.environ['JUPYTERHUB_SECRETS_DIR']}/jupyterhub_cookie_secret"
c.JupyterHub.db_url = f"sqlite:///{os.environ['JUPYTERHUB_SECRETS_DIR']}/jupyterhub.sqlite"

c.JupyterHub.spawner_class = VirtualEnvSpawner

# Create a group to indicate users with read/write access to MinIO
c.JupyterHub.load_groups = {
    VirtualEnvSpawner.RW_MINIO_GROUP: [],
}

# Set the JupyterHub IP address and port
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = int(os.getenv('NOTEBOOK_PORT'))

c.JupyterHub.log_level = 'DEBUG'
