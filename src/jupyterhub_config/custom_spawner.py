import fcntl
import os
import pwd
import subprocess
import tempfile
from pathlib import Path

from jupyterhub.spawner import SimpleLocalProcessSpawner


class VirtualEnvSpawner(SimpleLocalProcessSpawner):
    """
    A custom JupyterHub spawner that creates and manages a virtual environment
    for each user, configuring their workspace based on their admin status.
    """

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

        # Ensure the user directory exists and has correct permissions
        self._ensure_user_directory(user_dir, username)

        # Ensure the user's Jupiter directory exists
        self._ensure_user_jupyter_directory(user_dir)

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
                    group_check = subprocess.run(['getent', 'group', group], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        Ensure the user's home directory exists and is correctly owned and permissioned.
        """
        if not user_dir.exists():
            self.log.info(f'Creating user directory for {username}')
            user_dir.mkdir(parents=True)

            # Get the Jupyter user's UID and GID
            user_info = pwd.getpwnam(username)
            uid = user_info.pw_uid
            gid = user_info.pw_gid

            # Change the directory's ownership to the user
            os.chown(user_dir, uid, gid)

            # Set directory permissions to 700: Owner (rwx), Group (---), Others (---)
            os.chmod(user_dir, 0o700)

        else:
            self.log.info(f'Reusing user directory for {username}')

    def _ensure_user_jupyter_directory(self, user_dir: Path):
        """
        Create the user's Jupyter directory and subdirectories if they do not exist. And set the
        environment variables for Jupyter to use these directories.
        """

        jupyter_dir = user_dir / '.jupyter'
        jupyter_runtime_dir = jupyter_dir / 'runtime'
        juputer_data_dir = jupyter_dir / 'data'

        jupyter_dir.mkdir(parents=True, exist_ok=True)
        jupyter_runtime_dir.mkdir(parents=True, exist_ok=True)
        juputer_data_dir.mkdir(parents=True, exist_ok=True)

        self.environment['JUPYTER_CONFIG_DIR'] = str(jupyter_dir)
        self.environment['JUPYTER_RUNTIME_DIR'] = str(jupyter_runtime_dir)
        self.environment['JUPYTER_DATA_DIR'] = str(juputer_data_dir)