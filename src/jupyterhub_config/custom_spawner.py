import fcntl
import os
import subprocess
import tempfile

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

        # Ensure the system user exists
        self._ensure_system_user(username, group='jupyterhub')

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
