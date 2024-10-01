import os
import venv
from pathlib import Path

import json5
from dockerspawner import DockerSpawner
from filelock import FileLock


class CustomDockerSpawner(DockerSpawner):
    RW_MINIO_GROUP = 'minio_rw'

    def start(self):
        username = self.user.name
        global_home = Path(os.environ['JUPYTERHUB_USER_HOME'])
        user_dir = global_home / username

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

        # Ensure the user's volume is correctly mounted in the container
        self._ensure_user_volume()

        # Add the user's home directory to JupyterLab favorites
        # TODO: include shared group directories in favorites
        self._add_favorite_dir(user_dir)

        return super().start()

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

        self.environment['JUPYTER_MODE'] = 'jupyterhub-singleuser'
        self.environment['JUPYTERHUB_ADMIN'] = self.user.admin

        self.log.info(f'Setting spark driver host to {self.container_name}')
        self.environment['SPARK_DRIVER_HOST'] = self.container_name

        self.environment['HOME'] = str(user_dir)
        self.environment['PATH'] = f"{user_env_dir}/bin:{os.environ['PATH']}"
        self.environment['VIRTUAL_ENV'] = str(user_env_dir)
        if 'PYTHONPATH' in os.environ:
            self.environment['PYTHONPATH'] = f"{user_env_dir}/lib/python3.11/site-packages:{os.environ['PYTHONPATH']}"
        else:
            self.environment['PYTHONPATH'] = f"{user_env_dir}/lib/python3.11/site-packages"

        # Set path of the startup script for Notebook
        self.environment['PYTHONSTARTUP'] = os.path.join(os.environ['JUPYTERHUB_CONFIG_DIR'], 'startup.py')
        self.environment['JUPYTERHUB_USER'] = username

        if self._is_rw_minio_user():
            self.log.info(f'MinIO read/write user detected: {self.user.name}. Setting up minio_rw credentials.')
            self.environment['MINIO_ACCESS_KEY'] = self.environment['MINIO_RW_ACCESS_KEY']
            self.environment['MINIO_SECRET_KEY'] = self.environment['MINIO_RW_SECRET_KEY']
        else:
            self.log.info(f'Non-admin user detected: {self.user.name}. Removing admin credentials.')
            self.environment.pop('MINIO_RW_ACCESS_KEY', None)
            self.environment.pop('MINIO_RW_SECRET_KEY', None)

        # TODO: add a white list of environment variables to pass to the user's environment
        self.environment.pop('JUPYTERHUB_ADMIN_PASSWORD', None)

        self.log.info(f"Environment variables for user '{self.user.name}' at container startup: {self.environment}")

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

    def _is_rw_minio_user(self):
        """
        Check if the user is a read/write MinIO user.

        Admin users and users in the minio_rw group are considered read/write MinIO users.
        """
        group_names = [group.name for group in self.user.groups]
        return self.user.admin or self.RW_MINIO_GROUP in group_names

    def _ensure_user_volume(self):
        """
        Ensure the user's volume is correctly mounted in the container.
        """

        user_home_dir = Path(os.environ['JUPYTERHUB_USER_HOME'])
        mount_base_dir = Path(os.environ['JUPYTERHUB_MOUNT_BASE_DIR'])
        hub_secrets_dir = Path(os.environ['JUPYTERHUB_SECRETS_DIR'])

        cdm_shared_dir = Path(os.environ['CDM_SHARED_DIR'])  # Legacy data volume from JupyterLab
        hive_metastore_dir = Path(os.environ['HIVE_METASTORE_DIR'])  # within cdm_shared_dir

        if self.user.admin:
            self.log.info(f'Admin user detected: {self.user.name}. Setting up admin mount points.')
            self.volumes.update({
                f'{mount_base_dir}/{user_home_dir}': f'{user_home_dir}',  # Global users home directory
                f'{mount_base_dir}/{hub_secrets_dir}': f'{hub_secrets_dir}',
                f'{mount_base_dir}/{cdm_shared_dir}': f'{cdm_shared_dir}',  # Legacy data volume from JupyterLab
            })
        else:
            self.log.info(f'Non-admin user detected: {self.user.name}. Setting up user-specific mount points.')
            access_mode = 'rw' if self._is_rw_minio_user() else 'ro'
            self.volumes.update({
                f'{mount_base_dir}/{hive_metastore_dir}': {'bind': f'{hive_metastore_dir}', 'mode': access_mode},
                # User specific home directory
                f'{mount_base_dir}/{user_home_dir}/{self.user.name}': f'{user_home_dir}/{self.user.name}'
            })

    def _add_favorite_dir(self, user_dir: Path, favorites: set[Path] = None):
        """
        Configure the JupyterLab favorites for the user.
        """
        self.log.info('Configuring JupyterLab favorites for user')

        # Ensure the user's home directory is always in the favorites
        favorites = {user_dir} if not favorites else favorites | {user_dir}

        # Path to the JupyterLab favorites configuration file
        jupyterlab_favorites_path = user_dir / '.jupyter' / 'lab' / 'user-settings' / '@jlab-enhanced' / 'favorites' / 'favorites.jupyterlab-settings'
        favorites_dir = jupyterlab_favorites_path.parent

        favorites_dir.mkdir(parents=True, exist_ok=True)

        # Create a file lock to prevent race conditions
        lock_path = str(jupyterlab_favorites_path) + ".lock"
        lock = FileLock(lock_path)

        with lock:
            if jupyterlab_favorites_path.exists():
                with open(jupyterlab_favorites_path, 'r') as f:
                    # JupyterHub writes JSON comments in the file
                    exist_favorites = json5.load(f)
            else:
                exist_favorites = {"favorites": []}

            existing_fav_set = {(fav["root"], fav["path"]) for fav in exist_favorites.get('favorites', [])}

            for fav in favorites:

                if not fav.is_dir():
                    raise ValueError(f"Favorite {fav} is not a directory or does not exist")

                root_str = str(fav)
                path_str = ""

                if (root_str, path_str) not in existing_fav_set:
                    exist_favorites["favorites"].append({
                        "root": root_str,
                        "path": path_str,
                        "contentType": "directory",
                        "iconLabel": "ui-components:folder",
                        "name": "$HOME" if root_str == str(user_dir) else fav.name,
                    })

            with open(jupyterlab_favorites_path, 'w') as f:
                json5.dump(exist_favorites, f, indent=4)
