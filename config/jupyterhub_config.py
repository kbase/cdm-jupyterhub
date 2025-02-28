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
from jupyterhub_config.custom_kube_spawner import CustomKubeSpawner
from jupyterhub_config.kb_jupyterhub_auth import KBaseAuthenticator, kbase_origin

c = get_config()

def get_bool_env(key, default=False):
    """Parse str boolean environment variables"""
    value = os.environ.get(key, str(default)).lower()
    return value in ('true', '1', 't')

# NOTE: Switching the authentication method can lead to unintended consequences. For example, if user A is identified
# as "Z" under local authentication while user B is identified as "Z" under KBase authentication, changing the auth
# implementation could reassign file ownership from one user to the other.
if get_bool_env('USE_KBASE_AUTHENTICATOR'):
    # Set the authenticator class to KBaseAuthenticator
    # ref: https://jupyterhub.readthedocs.io/en/latest/reference/authenticators.html#authenticators
    c.JupyterHub.authenticator_class = KBaseAuthenticator
    c.Authenticator.enable_auth_state = True  # Enable authentication state persistence
    c.JupyterHub.template_paths = [os.environ['JUPYTERHUB_TEMPLATES_DIR']]
    c.JupyterHub.template_vars = {
        'kbase_origin': f'https://{kbase_origin()}'
    }
else:
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

# Create a group to indicate users with read/write access to MinIO
c.JupyterHub.load_groups = {
    CustomDockerSpawner.RW_MINIO_GROUP: [],
}

if get_bool_env('USE_KUBE_SPAWNER', True):
    # Hub configuration for Kubernetes
    c.JupyterHub.hub_ip = '0.0.0.0'
    c.JupyterHub.hub_port = 8081
    c.JupyterHub.bind_url = 'http://0.0.0.0:8081'

    spawner_class = CustomKubeSpawner
    spawner_config = c.KubeSpawner

    # User Kubernetes pod configuration
    c.KubeSpawner.namespace = os.environ['KUBE_NAMESPACE']
    c.KubeSpawner.hub_connect_url = f"http://{os.environ['SPARK_DRIVER_HOST']}:8081"

    def modify_pod_hook(spawner, pod):
        pod.spec.service_account_name = "cdm-jupyterhub"
        # Add a label to the pod to identify it as a JupyterHub pod
        # Ref: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
        pod.metadata.labels.update({"app": "cdm-jupyterhub"})
        pod.spec.dns_policy = "ClusterFirstWithHostNet"
        return pod
    c.KubeSpawner.modify_pod_hook = modify_pod_hook
    c.KubeSpawner.image_pull_policy = 'IfNotPresent'

    c.KubeSpawner.delete_stopped_pods = get_bool_env('REMOVE_STOPPED_CONTAINER_AND_POD', True)
else:
    spawner_class = CustomDockerSpawner
    spawner_config = c.DockerSpawner

    # User Docker container configuration
    c.DockerSpawner.hub_connect_url = f"http://{os.environ['SPARK_DRIVER_HOST']}:{os.environ['NOTEBOOK_PORT']}"
    c.DockerSpawner.cmd = ['echo', 'Starting JupyterHub Single User Server With DockerSpawner ...']
    c.DockerSpawner.cpu_limit = 4
    c.DockerSpawner.mem_limit = '16G'

    # The network name that Docker containers will use to communicate
    if network_name := os.environ.get('NETWORK_NAME'):
        c.DockerSpawner.network_name = network_name
    c.DockerSpawner.use_internal_ip = True
    c.DockerSpawner.extra_create_kwargs = {'labels': {'io.rancher.container.network': 'true'}}

    c.DockerSpawner.remove = get_bool_env('REMOVE_STOPPED_CONTAINER_AND_POD', True)

# Set the custom spawner class for the JupyterHub server
c.JupyterHub.spawner_class = spawner_class

# Common container settings
spawner_config.image = os.environ['JUPYTERHUB_USER_IMAGE']  # Set the Docker image to use for user containers
spawner_config.http_timeout = 120  # 2 minutes (default is 30 seconds)
spawner_config.start_timeout = 300  # 5 minutes (default is 60 seconds)
spawner_config.debug = True

# Set the JupyterHub IP address and port
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = int(os.getenv('NOTEBOOK_PORT'))

c.JupyterHub.log_level = 'DEBUG'
