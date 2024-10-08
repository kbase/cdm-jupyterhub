import fcntl
import grp
import os
import pwd
import subprocess
import tempfile
import venv
from pathlib import Path

from jupyterhub.spawner import SimpleLocalProcessSpawner


class VirtualEnvSpawner(SimpleLocalProcessSpawner):
    """
    A custom JupyterHub spawner that creates and manages a virtual environment
    for each user, configuring their workspace based on their admin status.
    """

    RW_MINIO_GROUP = 'minio_rw'

    def start(self):
        """
        Start the JupyterHub server for the user. This method ensures that the
        user's directory and virtual environment are set up, configures environment
        variables, and sets the notebook directory before starting the server.
        """

        username = self.user.name
        global_home = Path(os.environ['JUPYTERHUB_USER_HOME'])
        user_dir = global_home / username

        # Ensure the system user exists
        self._ensure_system_user(username, group='jupyterhub')

        # Ensure the user directory exists
        self._ensure_user_directory(user_dir, username)

        # Ensure the user's Jupyter directory exists
        self._ensure_user_jupyter_directory(user_dir)

        # Ensure the virtual environment is created or reused
        user_env_dir = user_dir / '.virtualenvs' / 'envs' / f'{username}_default_env'
        self._ensure_virtual_environment(user_env_dir)

        # Configure the environment variables specific to the user's virtual environment
        self._configure_environment(user_dir, user_env_dir, username)

        # Configure the notebook directory based on whether the user is an admin
        self._configure_notebook_dir(username, user_dir)

        # Ensure the user's workspace has the correct permissions
        self._ensure_workspace_permission(user_dir, username)

        # Set the command to start the notebook
        env_vars = [f'{key}={value}' for key, value in self.environment.items()]

        self.cmd = ['sudo', '-E', '-u', username, 'env'] + env_vars + [
            os.path.join(os.environ['JUPYTERHUB_CONFIG_DIR'], 'spawn_notebook.sh')]

        return super().start()

    def _ensure_system_user(self, username: str, group: str = None):
        """
        Create a system user with the given username if it does not already exist.
        Ensure the group exists before creating the user.
        Use a file lock to prevent race conditions.
        """

        lock_file = os.path.join(tempfile.gettempdir(), f'user_creation_{username}.lock')

        with open(lock_file, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                # Check if user already exists
                result = subprocess.run(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    self.log.info(f'User {username} already exists')
                    return

                # Create the user
                self.log.info(f'Creating system user: {username}')
                useradd_cmd = ['sudo', 'useradd', '-r']

                if group:
                    # Check if the group exists, create if necessary
                    group_check = subprocess.run(['getent', 'group', group],
                                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if group_check.returncode != 0:
                        self.log.info(f'Group {group} does not exist, creating it.')
                        subprocess.run(['sudo', 'groupadd', group], check=True)
                    else:
                        self.log.info(f'Group {group} already exists')

                    useradd_cmd.extend(['-g', group])

                useradd_cmd.append(username)

                subprocess.run(useradd_cmd, check=True)

            except subprocess.CalledProcessError as e:
                raise ValueError(f'Failed to create system user: {e}')

            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _ensure_user_directory(self, user_dir: Path, username: str):
        """
        Ensure the user's home directory exists.
        """
        if not user_dir.exists():
            self.log.info(f'Creating user directory for {username}')
            user_dir.mkdir(parents=True, exist_ok=True)  # guard against race conditions
        else:
            self.log.info(f'Reusing user directory for {username}')

    def _ensure_user_jupyter_directory(self, user_dir: Path):
        """
        Create the user's Jupyter directory and subdirectories if they do not exist. And set the
        environment variables for Jupyter to use these directories.
        """

        if not user_dir.exists():
            raise ValueError(f'User directory {user_dir} does not exist')

        jupyter_dir = user_dir / '.jupyter'
        jupyter_runtime_dir = jupyter_dir / 'runtime'
        juputer_data_dir = jupyter_dir / 'data'

        jupyter_dir.mkdir(parents=True, exist_ok=True)
        jupyter_runtime_dir.mkdir(parents=True, exist_ok=True)
        juputer_data_dir.mkdir(parents=True, exist_ok=True)

        self.environment['JUPYTER_CONFIG_DIR'] = str(jupyter_dir)
        self.environment['JUPYTER_RUNTIME_DIR'] = str(jupyter_runtime_dir)
        self.environment['JUPYTER_DATA_DIR'] = str(juputer_data_dir)

    def _ensure_virtual_environment(self, user_env_dir: Path):
        """
        Ensure the user's virtual environment exists. If it does not exist, it is
        created with the system site-packages included.
        """
        if not user_env_dir.exists():
            user_env_dir.mkdir(parents=True, exist_ok=True)
            self.log.info(f'Creating virtual environment for {self.user.name}')
            try:
                # Create a virtual environment with system site-packages access
                venv.create(env_dir=user_env_dir, system_site_packages=True, with_pip=True)
            except Exception as e:
                raise ValueError(f'Failed to create virtual environment for {self.user.name}: {e}') from e
        else:
            self.log.info(f'Reusing virtual environment for {self.user.name}')

    def _configure_environment(self, user_dir: Path, user_env_dir: Path, username: str):
        """
        Configure the environment variables for the user's session, including
        the PATH and PYTHONPATH to use the virtual environment.
        """
        self.environment.update({key: value for key, value in os.environ.items() if key not in self.environment})

        self.environment['HOME'] = str(user_dir)
        self.environment['PATH'] = f"{user_env_dir}/bin:{os.environ['PATH']}"
        if 'PYTHONPATH' in os.environ:
            self.environment['PYTHONPATH'] = f"{user_env_dir}/lib/python3.11/site-packages:{os.environ['PYTHONPATH']}"
        else:
            self.environment['PYTHONPATH'] = f"{user_env_dir}/lib/python3.11/site-packages"

        # Set path of the startup script for Notebook
        self.environment['PYTHONSTARTUP'] = os.path.join(os.environ['JUPYTERHUB_CONFIG_DIR'], 'startup.py')
        self.environment['JUPYTERHUB_USER'] = username

        group_names = [group.name for group in self.user.groups]
        self.log.info(f'User {self.user.name} groups: {group_names}')

        if self.user.admin or self.RW_MINIO_GROUP in group_names:
            self.log.info(f'MinIO read/write user detected: {username}. Setting up minio_rw credentials.')
            self.environment['MINIO_ACCESS_KEY'] = self.environment['MINIO_RW_ACCESS_KEY']
            self.environment['MINIO_SECRET_KEY'] = self.environment['MINIO_RW_SECRET_KEY']
        else:
            self.log.info(f'Non-admin user detected: {username}. Removing admin credentials.')
            self.environment.pop('MINIO_RW_ACCESS_KEY', None)
            self.environment.pop('MINIO_RW_SECRET_KEY', None)

        # TODO: add a white list of environment variables to pass to the user's environment
        self.environment.pop('JUPYTERHUB_ADMIN_PASSWORD', None)

        self.log.info(f"Environment variables for {username}: {self.environment}")

    def _configure_notebook_dir(self, username: str, user_dir: Path):
        """
        Configure the notebook directory for the user. If the user is an admin,
        the directory is set to a shared workspace. Otherwise, it is set to the
        user's home directory.
        """
        if self.user.admin:
            self.log.info(f'Admin user detected: {username}. Setting up admin workspace.')
            # root directory
            self.notebook_dir = str('/')
        else:
            self.log.info(f'Non-admin user detected: {username}. Setting up user-specific workspace.')
            self.notebook_dir = str(user_dir)

    def _ensure_workspace_permission(self, user_dir: Path, username: str):
        """
        Ensure the user's workspace has the correct permissions.
        """
        try:
            user_info = pwd.getpwnam(username)
        except KeyError:
            raise ValueError(f'System user {username} does not exist')
        gid = user_info.pw_gid
        group_name = grp.getgrgid(gid).gr_name

        self.log.info(f'Configuring workspace permissions for {username}')
        # Change the directory's ownership to the user
        subprocess.run(['sudo', 'chown', '-R', f'{username}:{group_name}', user_dir], check=True)

        self.log.info(f'Add spark_user to the group of {group_name}')
        subprocess.run(['sudo', 'usermod', '-aG', group_name, 'spark_user'], check=True)

        # TODO: Set directory permissions to 750 or 700 or switch to use docker spawner
        # Set directory permissions to 777: Owner (rwx), Group (rwx), Others (rwx)
        subprocess.run(['sudo', 'chmod', '-R', '777', user_dir], check=True)
