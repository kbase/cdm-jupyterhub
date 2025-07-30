import os
import shutil
import venv
from datetime import datetime, timedelta
from pathlib import Path

import json5
from dockerspawner import DockerSpawner
from filelock import FileLock

from minio_governance.client import DataGovernanceClient


class CustomDockerSpawner(DockerSpawner):
    RW_MINIO_GROUP = "minio_rw"
    DEFAULT_IDLE_TIMEOUT_MINUTES = 180

    def start(self):
        username = self.user.name
        global_home = Path(os.environ["JUPYTERHUB_USER_HOME"])
        user_dir = global_home / username
        self.idle_timeout = self._get_idle_timeout()

        # Ensure the user directory exists
        self._ensure_user_directory(user_dir, username)
        self._ensure_bashrc(user_dir)

        # Ensure the user's Jupyter directory exists
        self._ensure_user_jupyter_directory(user_dir)

        # Ensure the virtual environment is created or reused
        user_env_dir = user_dir / ".virtualenvs" / "envs" / f"{username}_default_env"
        self._ensure_virtual_environment(user_env_dir)

        # Configure the environment variables specific to the user's virtual environment
        self._configure_environment(user_dir, user_env_dir, username)

        # Configure the notebook directory based on whether the user is an admin
        self._configure_notebook_dir(username, user_dir)

        # Ensure the user's volume is correctly mounted in the container
        self._ensure_user_volume()

        # Add the user's home and group shared directory to Jupyterhub favorites
        self._add_favorite_dir(
            user_dir, favorites={Path(os.environ["KBASE_GROUP_SHARED_DIR"])}
        )

        return super().start()

    def _get_idle_timeout(self):
        """
        Retrieves the idle timeout from the environment variable `IDLE_TIMEOUT_MINUTES`.
        If not set, defaults to 180 minutes.

        Returns:
            timedelta: Idle timeout duration.
        """
        idle_timeout_minutes = int(
            os.getenv("IDLE_TIMEOUT_MINUTES", self.DEFAULT_IDLE_TIMEOUT_MINUTES)
        )
        self.log.info(f"Idle timeout set to {idle_timeout_minutes} minutes")
        return timedelta(minutes=idle_timeout_minutes)

    async def poll(self):
        """
        Overrides the poll method to periodically check the status of the user’s JupyterHub container.

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
        self.log.info(f"Last activity for {self.container_name}: {last_activity}")

        if last_activity:
            idle_time = datetime.now() - last_activity
            self.log.info(f"Idle time for {self.container_name}: {idle_time}")

            if idle_time > self.idle_timeout:
                self.log.warn(
                    f"Container {self.container_name} has been idle for {idle_time}. Stopping..."
                )
                await self.stop()
                return 0  # Return an exit code to indicate the container has stopped

        # Return status (None) to indicate that the container is still running and active
        return status

    def _ensure_user_directory(self, user_dir: Path, username: str):
        """
        Ensure the user's home directory exists.
        """
        if not user_dir.exists():
            self.log.info(f"Creating user directory for {username}")
            user_dir.mkdir(parents=True, exist_ok=True)  # guard against race conditions
        else:
            self.log.info(f"Reusing user directory for {username}")

    def _ensure_bashrc(self, user_dir: Path):
        """
        Ensure the user's .bashrc and .bash_profile files exist, copying them from .tmpl templates if needed.
        """

        config_dir = Path(os.environ["CONFIG_DIR"])
        bashrc_tmpl = config_dir / ".bashrc.tmpl"
        bash_profile_tmpl = config_dir / ".bash_profile.tmpl"

        # Keep a copy of the template files in the user's home directory in case they are needed later
        # for recovery or debugging. They are not used by the user's shell.
        shutil.copy2(bashrc_tmpl, user_dir / ".bashrc.tmpl")
        shutil.copy2(bash_profile_tmpl, user_dir / ".bash_profile.tmpl")

        bashrc_dest = user_dir / ".bashrc"
        bash_profile_dest = user_dir / ".bash_profile"

        if not bashrc_dest.exists():
            self.log.info(f"Creating .bashrc file for {user_dir}")
            shutil.copy2(bashrc_tmpl, bashrc_dest)

        if not bash_profile_dest.exists():
            self.log.info(f"Creating .bash_profile file for {user_dir}")
            shutil.copy2(bash_profile_tmpl, bash_profile_dest)

    def _ensure_user_jupyter_directory(self, user_dir: Path):
        """
        Create the user's Jupyter directory and subdirectories if they do not exist. And set the
        environment variables for Jupyter to use these directories.
        """

        if not user_dir.exists():
            raise ValueError(f"User directory {user_dir} does not exist")

        jupyter_dir = user_dir / ".jupyter"
        jupyter_runtime_dir = jupyter_dir / "runtime"
        juputer_data_dir = jupyter_dir / "data"

        jupyter_dir.mkdir(parents=True, exist_ok=True)
        jupyter_runtime_dir.mkdir(parents=True, exist_ok=True)
        juputer_data_dir.mkdir(parents=True, exist_ok=True)

        # copy the jupyter_jupyter_ai_config.json file to the user's .jupyter directory
        # ref: https://jupyter-ai.readthedocs.io/en/latest/users/index.html#configuring-as-a-config-file
        jupyter_notebook_config = (
            Path(os.environ["JUPYTERHUB_CONFIG_DIR"])
            / os.environ["JUPYTER_AI_CONFIG_FILE"]
        )
        shutil.copy2(
            jupyter_notebook_config, jupyter_dir / os.environ["JUPYTER_AI_CONFIG_FILE"]
        )

        self.environment["JUPYTER_CONFIG_DIR"] = str(jupyter_dir)
        self.environment["JUPYTER_RUNTIME_DIR"] = str(jupyter_runtime_dir)
        self.environment["JUPYTER_DATA_DIR"] = str(juputer_data_dir)

    def _ensure_virtual_environment(self, user_env_dir: Path):
        """
        Ensure the user's virtual environment exists. If it does not exist, it is
        created with the system site-packages included.
        """
        if not user_env_dir.exists():
            user_env_dir.mkdir(parents=True, exist_ok=True)
            self.log.info(f"Creating virtual environment for {self.user.name}")
            try:
                # Create a virtual environment with system site-packages access
                venv.create(
                    env_dir=user_env_dir, system_site_packages=True, with_pip=True
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to create virtual environment for {self.user.name}: {e}"
                ) from e
        else:
            self.log.info(f"Reusing virtual environment for {self.user.name}")

    def _configure_environment(self, user_dir: Path, user_env_dir: Path, username: str):
        """
        Configure the environment variables for the user's session, including
        the PATH and PYTHONPATH to use the virtual environment.
        """
        self.environment.update(
            {
                key: value
                for key, value in os.environ.items()
                if key not in self.environment
            }
        )

        self.environment["JUPYTER_MODE"] = "jupyterhub-singleuser"
        self.environment["JUPYTERHUB_ADMIN"] = self.user.admin

        self.log.info(f"Setting spark driver host to {self.container_name}")
        self.environment["SPARK_DRIVER_HOST"] = self.container_name

        self.environment["HOME"] = str(user_dir)
        self.environment["PATH"] = f"{user_env_dir}/bin:{os.environ['PATH']}"
        self.environment["VIRTUAL_ENV"] = str(user_env_dir)
        if "PYTHONPATH" in os.environ:
            self.environment["PYTHONPATH"] = (
                f"{user_env_dir}/lib/python3.11/site-packages:{os.environ['PYTHONPATH']}"
            )
        else:
            self.environment["PYTHONPATH"] = (
                f"{user_env_dir}/lib/python3.11/site-packages"
            )

        # Set path of the startup script for Notebook
        self.environment["PYTHONSTARTUP"] = os.path.join(
            os.environ["JUPYTERHUB_CONFIG_DIR"], "startup.py"
        )
        self.environment["JUPYTERHUB_USER"] = username
        self.environment["SPARK_JOB_LOG_DIR_CATEGORY"] = username

        self.environment["SHELL"] = "/usr/bin/bash"

        # Get user-specific MinIO credentials from governance service
        # Check if KBASE_AUTH_TOKEN is available (should be set by pre_spawn_start)
        kbase_token = self.environment.get("KBASE_AUTH_TOKEN")
        if not kbase_token:
            raise ValueError(
                "KBASE_AUTH_TOKEN not found in spawner environment. Authentication required for governance client."
            )

        # Initialize governance client with the token directly
        client = DataGovernanceClient(kbase_token=kbase_token)

        # Get credentials for the current user
        credentials = client.get_credentials()
        self.log.info(
            f"Retrieved governance credentials for user {username}: access_key='{credentials.access_key}'"
        )

        if self.environment.get("USE_DATA_GOVERNANCE_CREDENTIALS", "false") == "true":
            # Set user-specific MinIO credentials
            self.environment["MINIO_ACCESS_KEY"] = credentials.access_key
            self.environment["MINIO_SECRET_KEY"] = credentials.secret_key
        else:
            if self._is_rw_minio_user():
                self.log.info(
                    f"MinIO read/write user detected: {self.user.name}. Setting up minio_rw credentials."
                )
                self.environment["MINIO_ACCESS_KEY"] = self.environment[
                    "MINIO_RW_ACCESS_KEY"
                ]
                self.environment["MINIO_SECRET_KEY"] = self.environment[
                    "MINIO_RW_SECRET_KEY"
                ]
                # USAGE_MODE is used by the setup.sh script to determine the appropriate configuration for the user.
                self.environment["USAGE_MODE"] = "dev"
            else:
                self.log.info(
                    f"Non-admin user detected: {self.user.name}. Removing admin credentials."
                )
                self.environment.pop("MINIO_RW_ACCESS_KEY", None)
                self.environment.pop("MINIO_RW_SECRET_KEY", None)

        # TODO: add a white list of environment variables to pass to the user's environment
        self.environment.pop("JUPYTERHUB_ADMIN_PASSWORD", None)

        self.log.info(
            f"Environment variables for user '{self.user.name}' at container startup: {self.environment}"
        )

    def _configure_notebook_dir(self, username: str, user_dir: Path):
        """
        Configure the notebook directory for the user. If the user is an admin,
        the directory is set to a shared workspace. Otherwise, it is set to the
        user's home directory.
        """
        if self.user.admin:
            self.log.info(
                f"Admin user detected: {username}. Setting up admin workspace."
            )
            # root directory
            self.notebook_dir = str("/")
        else:
            self.log.info(
                f"Non-admin user detected: {username}. Setting up user-specific workspace."
            )
            # TODO: It appears that notebook_dir must be the parent of the favorites directory - investigate if it's possible to set notebook_dir to user_dir
            # self.notebook_dir = str(user_dir)
            self.notebook_dir = str("/")

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

        user_home_dir = Path(os.environ["JUPYTERHUB_USER_HOME"])
        mount_base_dir = Path(os.environ["JUPYTERHUB_MOUNT_BASE_DIR"])
        hub_secrets_dir = Path(os.environ["JUPYTERHUB_SECRETS_DIR"])

        cdm_shared_dir = Path(
            os.environ["CDM_SHARED_DIR"]
        )  # Legacy data volume from JupyterLab
        kbase_shared_dir = Path(
            os.environ["KBASE_GROUP_SHARED_DIR"]
        )  # within cdm_shared_dir

        if self.user.admin:
            self.log.info(
                f"Admin user detected: {self.user.name}. Setting up admin mount points."
            )
            self.volumes.update(
                {
                    f"{mount_base_dir}/{user_home_dir}": f"{user_home_dir}",  # Global users home directory
                    f"{mount_base_dir}/{hub_secrets_dir}": f"{hub_secrets_dir}",
                    f"{mount_base_dir}/{cdm_shared_dir}": f"{cdm_shared_dir}",  # Legacy data volume from JupyterLab
                }
            )
        else:
            self.log.info(
                f"Non-admin user detected: {self.user.name}. Setting up user-specific mount points."
            )
            access_mode = "rw" if self._is_rw_minio_user() else "ro"
            self.volumes.update(
                {
                    # User specific home directory
                    f"{mount_base_dir}/{user_home_dir}/{self.user.name}": f"{user_home_dir}/{self.user.name}",
                    f"{mount_base_dir}/{kbase_shared_dir}": f"{kbase_shared_dir}",
                }
            )

    def _add_favorite_dir(self, user_dir: Path, favorites: set[Path] | None = None):
        """
        Configure the JupyterLab favorites for the user.
        """
        self.log.info("Configuring JupyterLab favorites for user")

        # Ensure the user's home directory is always in the favorites
        favorites = {user_dir} if not favorites else favorites | {user_dir}

        # Path to the JupyterLab favorites configuration file
        jupyterlab_favorites_path = (
            user_dir
            / ".jupyter"
            / "lab"
            / "user-settings"
            / "@jlab-enhanced"
            / "favorites"
            / "favorites.jupyterlab-settings"
        )
        favorites_dir = jupyterlab_favorites_path.parent

        favorites_dir.mkdir(parents=True, exist_ok=True)

        # Create a file lock to prevent race conditions
        lock_path = str(jupyterlab_favorites_path) + ".lock"
        lock = FileLock(lock_path)

        with lock:
            if jupyterlab_favorites_path.exists():
                with open(jupyterlab_favorites_path, "r") as f:
                    # JupyterHub writes JSON comments in the file
                    exist_favorites = json5.load(f)
            else:
                exist_favorites = {"favorites": []}

            existing_fav_set = {
                (fav["root"], fav["path"])
                for fav in exist_favorites.get("favorites", [])
            }

            for fav in favorites:

                if not fav.is_dir():
                    raise ValueError(
                        f"Favorite {fav} is not a directory or does not exist"
                    )

                # same approach used by NERSC JupyterHub
                root_str = "/"
                path_str = str(fav.relative_to(root_str))

                if (root_str, path_str) not in existing_fav_set:
                    exist_favorites["favorites"].append(
                        {
                            "root": root_str,
                            "path": path_str,
                            "contentType": "directory",
                            "iconLabel": "ui-components:folder",
                            "name": "$HOME" if str(fav) == str(user_dir) else fav.name,
                        }
                    )

            with open(jupyterlab_favorites_path, "w") as f:
                json5.dump(exist_favorites, f, indent=4)
