import fcntl
import grp
import logging
import os
import pwd
import socket
import subprocess
import tempfile
from pathlib import Path


class SingleUserEnvManager:
    """
    Manages the environment and user-specific settings for a single user in a JupyterHub server.
    """

    def __init__(self,
                 username,
                 groupname: str = 'jupyterhub', ):
        """
        Initializes the environment manager for the specified user.
        :param username: The name of the user for whom the environment is set up.
        :param groupname: The name of the OS system group to which the user belongs.
        """
        self.username = username  # OS system username
        self.groupname = groupname  # OS system group

        self.log = self._init_logger()

        # Inherit the current environment variables
        self.environment = dict(os.environ)

        # TODO: config Rancher to resolve the container hostname automatically within network
        # ip = self._get_container_ip()
        # self.log.info(f'Setting SPARK_DRIVER_HOST to {ip}')
        # self.environment['SPARK_DRIVER_HOST'] = ip

        self.global_home = Path(os.environ['JUPYTERHUB_USER_HOME'])
        self.user_dir = self.global_home / username


    def setup_environment(self):
        """
        Set up the user's environment by ensuring the system user exists, and the workspace
        permissions are correctly configured.
        """
        self.log.info(f"Setting up environment for user: {self.username}")
        self._ensure_system_user()
        self._ensure_workspace_permission()

    def start_single_user_server(self):
        """
        Starts the single-user Jupyter server for the user, inheriting the configured environment.
        """
        self.log.info(f'Starting single-user server for {self.username} with environment: {self.environment}')
        env_vars = [f'{key}={value}' for key, value in self.environment.items()]

        cmd = ['sudo', '-E', '-u', self.username, 'env'] + env_vars + [
            os.path.join(os.environ['JUPYTERHUB_CONFIG_DIR'], 'spawn_notebook.sh')]

        self.log.info(f'Executing command: {" ".join(cmd)}')
        subprocess.run(cmd, check=True)

    def _ensure_system_user(self):
        """
        Create a system user with the given username if it does not already exist.
        Ensure the group exists before creating the user.
        Use a file lock to prevent race conditions.
        """

        lock_file = os.path.join(tempfile.gettempdir(), f'user_creation_{self.username}.lock')

        with open(lock_file, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                # Check if user already exists
                try:
                    pwd.getpwnam(self.username)
                    self.log.info(f'User {self.username} already exists')
                    return
                except KeyError:

                    # Create the user
                    self.log.info(f'Creating system user: {self.username}')
                    useradd_cmd = ['sudo', 'useradd', '-r']

                    if self.groupname:
                        # Check if the group exists, create if necessary
                        try:
                            grp.getgrnam(self.groupname)
                            self.log.info(f'Group {self.groupname} already exists')
                        except KeyError:
                            self.log.info(f'Group {self.groupname} does not exist, creating it.')
                            subprocess.run(['sudo', 'groupadd', self.groupname], check=True)

                        useradd_cmd.extend(['-g', self.groupname])

                    useradd_cmd.append(self.username)

                    self.log.info(f'Creating system user: {self.username}')
                    subprocess.run(useradd_cmd, check=True)

            except subprocess.CalledProcessError as e:
                raise ValueError(f'Failed to create system user: {e}')

            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _ensure_workspace_permission(self):
        """
        Ensure the user's workspace has the correct permissions.
        """
        try:
            user_info = pwd.getpwnam(self.username)
        except KeyError:
            raise ValueError(f'System user {self.username} does not exist')
        gid = user_info.pw_gid
        group_name = grp.getgrgid(gid).gr_name

        self.log.info(f'Configuring workspace permissions for {self.username}')
        subprocess.run(['sudo', 'chown', '-R', f'{self.username}:{group_name}', self.user_dir], check=True)
        subprocess.run(['sudo', 'chmod', '-R', '750', self.user_dir], check=True)

    def _get_container_ip(self):
        """
        Get the IP address of the container.
        """
        self.log.info('Getting container IP address')
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address

    def _init_logger(self):
        """
        Initializes a logger for tracking the operations performed for the user.
        """
        logger = logging.getLogger(self.username)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger


def main():
    print("Starting hub_singleuser.py...")

    username = os.getenv('JUPYTERHUB_USER')

    if not username:
        raise ValueError('JUPYTERHUB_USER environment variable not set')

    single_user_manager = SingleUserEnvManager(username)
    single_user_manager.setup_environment()
    single_user_manager.start_single_user_server()


if __name__ == "__main__":
    main()
