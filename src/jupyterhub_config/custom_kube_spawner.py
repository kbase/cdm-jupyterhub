import os
import shutil
import venv
from datetime import datetime, timedelta
from pathlib import Path

import json5
from filelock import FileLock
from kubespawner import KubeSpawner

from service.arg_checkers import not_falsy
from spark import cluster


class CustomKubeSpawner(KubeSpawner):
    RW_MINIO_GROUP = 'minio_rw'
    DEFAULT_IDLE_TIMEOUT_MINUTES = 180

    def start(self):
        username = self.user.name
        global_home = Path(os.environ['JUPYTERHUB_USER_HOME'])
        user_dir = global_home / username
        self.idle_timeout = self._get_idle_timeout()

        # Ensure the user directory exists
        self._ensure_user_directory(user_dir, username)
        self._ensure_bashrc(user_dir)

        # Ensure the user's Jupyter directory exists
        self._ensure_user_jupyter_directory(user_dir)

        # Ensure the virtual environment is created or reused
        user_env_dir = user_dir / '.virtualenvs' / 'envs' / f'{username}_default_env'
        self._ensure_virtual_environment(user_env_dir)

        # Configure environment variables for the pod
        self._configure_environment(user_dir, user_env_dir, username)

        # Configure notebook directory
        self._configure_notebook_dir(username, user_dir)

        # Set up volume mounts specific for Kubernetes
        self._ensure_user_volume(user_dir)

        # Set up JupyterLab favorites (if applicable)
        self._add_favorite_dir(user_dir, favorites={Path(os.environ['KBASE_GROUP_SHARED_DIR'])})

        self.namespace = os.environ['KUBE_NAMESPACE']

        # Finally, create a Spark cluster for the user
        self._start_spark_cluster(username, not_falsy(self.environment['KBASE_AUTH_TOKEN'], 'KBASE_AUTH_TOKEN'))

        return super().start()

    async def stop(self, now=False):
        """Override the stop method with additional Spark cluster cleanup"""

        # Delete the user's Spark cluster
        self._stop_spark_cluster(self.user.name, not_falsy(self.environment['KBASE_AUTH_TOKEN'], 'KBASE_AUTH_TOKEN'))

        # Call the parent class's stop method to stop the pod
        return await super().stop(now=now)

    def _start_spark_cluster(self, username: str, kbase_auth_token: str):
        """
        Create a Spark cluster for the user
        """
        try:
            self.log.info(f"Creating Spark cluster for user {username}")
            response = cluster.create_cluster(kbase_auth_token=kbase_auth_token)
            if response and hasattr(response, 'master_url') and response.master_url:
                self.log.info(f"Spark cluster created with master URL: {response.master_url}")
                # Update environment with the Spark master URL
                self.environment['SPARK_MASTER_URL'] = response.master_url
            else:
                raise ValueError(f"Master URL not found in response: {response}")
        except Exception as e:
            self.log.error(f"Error creating Spark cluster for user {username}: {str(e)}")

    def _stop_spark_cluster(self, username: str, kbase_auth_token: str):
        """
        Delete the Spark cluster for the user
        """
        try:
            self.log.info(f"Deleting Spark cluster for user {username}")
            cluster.delete_cluster(kbase_auth_token=kbase_auth_token)
            self.log.info(f"Spark cluster deleted for user {username}")
        except Exception as e:
            self.log.error(f"Error deleting Spark cluster for user {username}: {str(e)}")

    def _get_idle_timeout(self):
        """
        Retrieves the idle timeout from the environment variable `IDLE_TIMEOUT_MINUTES`.
        If not set, defaults to 180 minutes.

        Returns:
            timedelta: Idle timeout duration.
        """
        idle_timeout_minutes = int(os.getenv("IDLE_TIMEOUT_MINUTES", self.DEFAULT_IDLE_TIMEOUT_MINUTES))
        self.log.info(f"Idle timeout set to {idle_timeout_minutes} minutes")
        return timedelta(minutes=idle_timeout_minutes)

    async def poll(self):
        """
        Overrides the poll method to periodically check the status of the user's JupyterHub container.

        ref:
        https://github.com/jupyterhub/dockerspawner/blob/main/dockerspawner/dockerspawner.py#L1004
        https://jupyterhub-dockerspawner.readthedocs.io/en/latest/api/index.html#dockerspawner.DockerSpawner.poll

        - If the container is stopped, returns the status immediately.
        - If the container is running, checks how long the user has been idle.
        - If idle time exceeds the defined threshold, stops the container to save resources.

        The poll method is invoked at regular intervals by the Spawner, with the frequency determined by the JupyterHub
        server's configuration (default is 30 seconds).

        Returns:
            int or None: Returns an exit code (0) if the container has been stopped due
                         to inactivity. Returns None if the container is still active
                         and running.
        """
        # Check if the container has already stopped
        status = await super().poll()
        if status is not None:
            # Container has already stopped, return its status code immediately
            return status

        last_activity = self.user.last_activity
        self.log.info(f"Last activity for {self.pod_name}: {last_activity}")
        if last_activity:
            idle_time = datetime.now() - last_activity
            self.log.info(f"Idle time for {self.pod_name}: {idle_time}")
            if idle_time > self.idle_timeout:
                self.log.warn(f"Pod {self.pod_name} has been idle for {idle_time}. Stopping...")
                await self.stop()
                return 0  # Return an exit code to indicate the container has stopped

        # Return status (None) to indicate that the container is still running and active
        return status

    def _ensure_user_directory(self, user_dir: Path, username: str):
        """
        Ensure the user's home directory exists.
        """
        if not user_dir.exists():
            self.log.info(f'Creating user directory for {username}')
            user_dir.mkdir(parents=True, exist_ok=True)  # guard against race conditions
        else:
            self.log.info(f'Reusing user directory for {username}')

    def _ensure_bashrc(self, user_dir: Path):
        """
        Ensure the user's .bashrc and .bash_profile files exist, copying them from .tmpl templates if needed.
        """

        config_dir = Path(os.environ['CONFIG_DIR'])
        bashrc_tmpl = config_dir / '.bashrc.tmpl'
        bash_profile_tmpl = config_dir / '.bash_profile.tmpl'

        # Keep a copy of the template files in the user's home directory in case they are needed later
        # for recovery or debugging. They are not used by the user's shell.
        shutil.copy2(bashrc_tmpl, user_dir / '.bashrc.tmpl')
        shutil.copy2(bash_profile_tmpl, user_dir / '.bash_profile.tmpl')

        bashrc_dest = user_dir / '.bashrc'
        bash_profile_dest = user_dir / '.bash_profile'

        if not bashrc_dest.exists():
            self.log.info(f'Creating .bashrc file for {user_dir}')
            shutil.copy2(bashrc_tmpl, bashrc_dest)

        if not bash_profile_dest.exists():
            self.log.info(f'Creating .bash_profile file for {user_dir}')
            shutil.copy2(bash_profile_tmpl, bash_profile_dest)

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

        # copy the jupyter_jupyter_ai_config.json file to the user's .jupyter directory
        # ref: https://jupyter-ai.readthedocs.io/en/latest/users/index.html#configuring-as-a-config-file
        jupyter_notebook_config = Path(os.environ['JUPYTERHUB_CONFIG_DIR']) / os.environ['JUPYTER_AI_CONFIG_FILE']
        shutil.copy2(jupyter_notebook_config, jupyter_dir / os.environ['JUPYTER_AI_CONFIG_FILE'])

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
        # In KubeSpawner, environment is a dict where the value can only be a strong
        # ref: https://jupyterhub-kubespawner.readthedocs.io/en/latest/spawner.html#kubespawner.KubeSpawner.environment
        self.environment.update({key: str(value) for key, value in os.environ.items() if key not in self.environment})

        self.environment['JUPYTER_MODE'] = 'jupyterhub-singleuser'
        self.environment['JUPYTERHUB_ADMIN'] = str(self.user.admin)

        self.log.info(f"Setting spark driver host to {self.pod_name}")
        self.environment['SPARK_DRIVER_HOST'] = self.pod_name

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

        self.environment['SHELL'] = '/usr/bin/bash'

        if self._is_rw_minio_user():
            self.log.info(f"MinIO read/write user detected: {self.user.name}. Setting up minio_rw credentials.")
            self.environment['MINIO_ACCESS_KEY'] = self.environment['MINIO_RW_ACCESS_KEY']
            self.environment['MINIO_SECRET_KEY'] = self.environment['MINIO_RW_SECRET_KEY']
            # USAGE_MODE is used by the setup.sh script to determine the appropriate configuration for the user.
            self.environment['USAGE_MODE'] = 'dev'
        else:
            self.log.info(f"Non-admin user detected: {self.user.name}. Removing admin credentials.")
            self.environment.pop('MINIO_RW_ACCESS_KEY', None)
            self.environment.pop('MINIO_RW_SECRET_KEY', None)

        # TODO: add a white list of environment variables to pass to the user's environment
        self.environment.pop('JUPYTERHUB_ADMIN_PASSWORD', None)

        self.log.info(f"Environment variables for user '{self.user.name}' at pod startup: {self.environment}")

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
            # TODO: It appears that notebook_dir must be the parent of the favorites directory - investigate if it's possible to set notebook_dir to user_dir
            # self.notebook_dir = str(user_dir)
            self.notebook_dir = str('/')

    def _is_rw_minio_user(self):
        """
        Check if the user is a read/write MinIO user.

        Admin users and users in the minio_rw group are considered read/write MinIO users.
        """
        group_names = [group.name for group in self.user.groups]
        return self.user.admin or self.RW_MINIO_GROUP in group_names

    def _ensure_user_volume(self, user_dir: Path):
        """
        Ensure the user's volume is correctly mounted in the container.
        """

        user_home_dir = os.environ['JUPYTERHUB_USER_HOME']
        mount_base_dir = os.environ['JUPYTERHUB_MOUNT_BASE_DIR']
        hub_secrets_dir = os.environ['JUPYTERHUB_SECRETS_DIR']

        cdm_shared_dir = os.environ['CDM_SHARED_DIR']  # Legacy data volume from JupyterLab
        hive_metastore_dir = os.environ['HIVE_METASTORE_DIR']  # within cdm_shared_dir
        kbase_shared_dir = os.environ['KBASE_GROUP_SHARED_DIR']  # within cdm_shared_dir

        if self.user.admin:
            self.log.info(f"Admin user detected: {self.user.name}. Setting up admin volume mounts.")
            self.volumes = [
                # Global users home directory
                {
                    "name": "user-home",
                    "hostPath": {"path": f"{mount_base_dir}/{user_home_dir}"}
                },
                {
                    "name": "jupyterhub-secrets",
                    "hostPath": {"path": f"{mount_base_dir}/{hub_secrets_dir}"}
                },
                # Legacy data volume from JupyterLab
                {
                    "name": "cdm-shared",
                    "hostPath": {"path": f"{mount_base_dir}/{cdm_shared_dir}"}
                }
            ]
            self.volume_mounts = [
                {"name": "user-home", "mountPath": user_home_dir},
                {"name": "jupyterhub-secrets", "mountPath": hub_secrets_dir},
                {"name": "cdm-shared", "mountPath": cdm_shared_dir}
            ]
        else:
            self.log.info(f"Non-admin user detected: {self.user.name}. Setting up user-specific volume mounts.")
            # Determine readOnly mode: True if NOT a read/write minio user
            read_only = not self._is_rw_minio_user()
            self.volumes = [
                {
                    "name": "hive-metastore",
                    "hostPath": {"path": f"{mount_base_dir}/{hive_metastore_dir}"}
                },
                # User specific home directory
                {
                    "name": "user-home",
                    "hostPath": {"path": f"{mount_base_dir}/{user_home_dir}/{self.user.name}"}
                },
                # Legacy data volume from JupyterLab
                {
                    "name": "kbase-shared",
                    "hostPath": {"path": f"{mount_base_dir}/{kbase_shared_dir}"}
                }
            ]
            self.volume_mounts = [
                {
                    "name": "hive-metastore",
                    "mountPath": hive_metastore_dir,
                    "readOnly": read_only
                },
                {
                    "name": "user-home",
                    "mountPath": f"{user_home_dir}/{self.user.name}"
                },
                {
                    "name": "kbase-shared",
                    "mountPath": kbase_shared_dir
                }
            ]

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

                # same approach used by NERSC JupyterHub
                root_str = "/"
                path_str = str(fav.relative_to(root_str))

                if (root_str, path_str) not in existing_fav_set:
                    exist_favorites["favorites"].append({
                        "root": root_str,
                        "path": path_str,
                        "contentType": "directory",
                        "iconLabel": "ui-components:folder",
                        "name": "$HOME" if str(fav) == str(user_dir) else fav.name,
                    })

            with open(jupyterlab_favorites_path, 'w') as f:
                json5.dump(exist_favorites, f, indent=4)