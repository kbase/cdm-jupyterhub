"""
This is the JupyterHub configuration file. It is used to configure the JupyterHub server.
Refer to the JupyterHub documentation for more information:
https://jupyterhub.readthedocs.io/en/latest/tutorial/getting-started/config-basics.html
https://jupyterhub.readthedocs.io/en/stable/reference/config-reference.html

Refer to DockerSpawner documentation for dockerspawner settings information:
https://jupyterhub-dockerspawner.readthedocs.io/en/latest/api/index.html#dockerspawner-api
"""

import os

import nativeauthenticator

from jupyterhub_config.custom_docker_spawner import CustomDockerSpawner

c = get_config()

# Set the authenticator class to nativeauthenticator
# ref: https://native-authenticator.readthedocs.io/en/latest/quickstart.html
c.JupyterHub.authenticator_class = 'native'
c.JupyterHub.template_paths = [
    os.environ['JUPYTERHUB_TEMPLATES_DIR'],
]
kbase_env = (os.environ['JUPYTERHUB_KB_ENV']).lower() if 'JUPYTERHUB_KB_ENV' in os.environ else "ci"
c.JupyterHub.template_vars = {
    'kbase_origin': 'https://narrative.kbase.us' if kbase_env == "prod" else f'https://{kbase_env}.kbase.us'
}
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

# Create a group to indicate users with read/write access to MinIO
c.JupyterHub.load_groups = {
    CustomDockerSpawner.RW_MINIO_GROUP: [],
}

c.JupyterHub.spawner_class = CustomDockerSpawner

c.DockerSpawner.hub_connect_url = f"http://{os.environ['SPARK_DRIVER_HOST']}:{os.environ['NOTEBOOK_PORT']}"
# Set the Docker image to use for user containers
c.DockerSpawner.image = os.environ['JUPYTERHUB_USER_IMAGE']

c.DockerSpawner.cmd = ['echo', 'Starting JupiterHub Single User Server With DockerSpawner ...']

# Container resource limits
c.DockerSpawner.cpu_limit = 4
c.DockerSpawner.mem_limit = '16G'

c.DockerSpawner.http_timeout = 120 # 2 minutes (default is 30 seconds)
c.DockerSpawner.start_timeout = 300  # 5 minutes (default is 60 seconds)

# The network name that Docker containers will use to communicate
network_name = os.environ.get('NETWORK_NAME')
if network_name:
    c.DockerSpawner.network_name = network_name
c.DockerSpawner.use_internal_ip = True
environment = os.environ.get('ENVIRONMENT', 'prod').lower()
# for troubleshooting purposes, keep the container in non-prod environment
c.DockerSpawner.remove = environment != 'dev'
c.DockerSpawner.debug = True

# Set extra labels in order to use Rancher's network policies
# ref: https://rancher.com/docs/rancher/v1.6/en/rancher-services/networking/#containers-created-with-the-docker-cli
c.DockerSpawner.extra_create_kwargs = {
    'labels': {
        'io.rancher.container.network': 'true'
    }
}

c.DockerSpawner.shutdown_no_activity_timeout = 60 * 60  # 1 hour

# Set the JupyterHub IP address and port
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = int(os.getenv('NOTEBOOK_PORT'))

c.JupyterHub.log_level = 'DEBUG'
