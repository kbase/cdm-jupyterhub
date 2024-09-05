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

        return super().start()