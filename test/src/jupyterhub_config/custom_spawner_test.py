import logging
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch, MagicMock

import pytest

from jupyterhub_config.custom_spawner import VirtualEnvSpawner


@pytest.fixture
def spawner():
    spawner = VirtualEnvSpawner()
    spawner.user = MagicMock()
    spawner.user.name = 'testuser'
    spawner.user.admin = False

    return spawner


@patch.dict(os.environ, {
    'JUPYTERHUB_USER_HOME': '/jupyterhub/users_home',
    'JUPYTERHUB_CONFIG_DIR': '/etc/jupyterhub'
})
@patch.object(VirtualEnvSpawner, '_ensure_system_user')
@patch.object(VirtualEnvSpawner, '_ensure_user_directory')
@patch.object(VirtualEnvSpawner, '_ensure_user_jupyter_directory')
@patch.object(VirtualEnvSpawner, '_ensure_virtual_environment')
@patch.object(VirtualEnvSpawner, '_configure_environment')
@patch.object(VirtualEnvSpawner, '_configure_notebook_dir')
def test_start(mock_configure_notebook_dir, mock_configure_environment, mock_ensure_virtual_environment,
               mock_ensure_user_jupyter_directory, mock_ensure_user_directory, mock_ensure_system_user,
               spawner):

    # set spawner.environment (_configure_environment is mocked, so `self.environment` won't be set by the method)
    spawner.environment = {
        'JUPYTERHUB_USER_HOME': '/jupyterhub/users_home',
        'JUPYTERHUB_CONFIG_DIR': '/etc/jupyterhub'
    }

    spawner.start()

    # Ensure each method is called in the specified order
    expected_calls = [
        unittest.mock.call('testuser', group='jupyterhub'),
        unittest.mock.call(Path('/jupyterhub/users_home/testuser'), 'testuser'),
        unittest.mock.call(Path('/jupyterhub/users_home/testuser')),
        unittest.mock.call(Path('/jupyterhub/users_home/testuser/.virtualenvs/envs/testuser_default_env')),
        unittest.mock.call(Path('/jupyterhub/users_home/testuser'),
                           Path('/jupyterhub/users_home/testuser/.virtualenvs/envs/testuser_default_env'),
                           'testuser'),
        unittest.mock.call('testuser', Path('/jupyterhub/users_home/testuser'))
    ]

    mock_ensure_system_user.assert_has_calls(expected_calls[0:1], any_order=False)
    mock_ensure_user_directory.assert_has_calls(expected_calls[1:2], any_order=False)
    mock_ensure_user_jupyter_directory.assert_has_calls(expected_calls[2:3], any_order=False)
    mock_ensure_virtual_environment.assert_has_calls(expected_calls[3:4], any_order=False)
    mock_configure_environment.assert_has_calls(expected_calls[4:5], any_order=False)
    mock_configure_notebook_dir.assert_has_calls(expected_calls[5:6], any_order=False)

    # Check if the command to start the notebook server is set correctly
    expected_cmd = [
        'sudo', '-E', '-u', 'testuser', 'env',
        f'JUPYTERHUB_USER_HOME=/jupyterhub/users_home',
        f'JUPYTERHUB_CONFIG_DIR=/etc/jupyterhub',
        '/etc/jupyterhub/spawn_notebook.sh'
    ]
    assert spawner.cmd == expected_cmd


# Test when the user already exists
@patch('subprocess.run')
def test_ensure_system_user_already_exists(mock_run, caplog):
    with caplog.at_level(logging.INFO):
        # Mock 'id' command to simulate user already exists
        mock_run.return_value.returncode = 0

        spawner = VirtualEnvSpawner()
        username = 'testuser'
        spawner._ensure_system_user(username)

        mock_run.assert_called_once_with(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        assert f'User {username} already exists' in caplog.text


# Test when the group and user need to be created
@patch('subprocess.run')
def test_ensure_system_user_create_group_and_user(mock_run, caplog):
    with caplog.at_level(logging.INFO):
        # Define side_effect to simulate user does not exist, group does not exist, and then successful creation
        mock_run.side_effect = [
            MagicMock(returncode=1),  # 'id' command: User does not exist
            MagicMock(returncode=2),  # 'getent' command: Group does not exist
            MagicMock(returncode=0),  # 'groupadd' command: Group created successfully
            MagicMock(returncode=0)  # 'useradd' command: User created successfully
        ]

        spawner = VirtualEnvSpawner()
        username = 'testuser'
        group = 'testgroup'
        spawner._ensure_system_user(username, group)

        expected_calls = [
            unittest.mock.call(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            unittest.mock.call(['getent', 'group', group], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            unittest.mock.call(['sudo', 'groupadd', group], check=True),
            unittest.mock.call(['sudo', 'useradd', '-r', '-g', group, username], check=True)
        ]

        # Check that the expected calls were made in order
        mock_run.assert_has_calls(expected_calls, any_order=False)

        assert f'Creating system user: {username}' in caplog.text
        assert f'Group {group} does not exist, creating it.' in caplog.text


# Test when the user is created without a group
@patch('subprocess.run')
def test_ensure_system_user_create_user_without_group(mock_run, caplog):
    with caplog.at_level(logging.INFO):
        # Mock the 'id' command to simulate user does not exist
        mock_run.side_effect = [
            MagicMock(returncode=1),  # User does not exist
            MagicMock(returncode=0)  # User created successfully
        ]

        spawner = VirtualEnvSpawner()
        username = 'testuser'
        spawner._ensure_system_user(username)

        assert f'Creating system user: {username}' in caplog.text
        expected_calls = [
            unittest.mock.call(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            unittest.mock.call(['sudo', 'useradd', '-r', username], check=True)
        ]

        mock_run.assert_has_calls(expected_calls, any_order=False)


# Test subprocess.CalledProcessError is handled correctly
@patch('subprocess.run')
def test_ensure_system_user_error(mock_run):
    # Mock the 'id' command to simulate user does not exist
    # Mock 'useradd' command to raise CalledProcessError
    mock_run.side_effect = [
        MagicMock(returncode=1),
        CalledProcessError(1, 'useradd')
    ]

    spawner = VirtualEnvSpawner()
    with pytest.raises(ValueError, match="Failed to create system user"):
        spawner._ensure_system_user('testuser')

    expected_calls = [
        unittest.mock.call(['id', 'testuser'], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        unittest.mock.call(['sudo', 'useradd', '-r', 'testuser'], check=True)
    ]

    mock_run.assert_has_calls(expected_calls, any_order=False)


@patch('pwd.getpwnam')
@patch('os.chown')
def test_ensure_user_directory_with_logging(mock_chown, mock_getpwnam, caplog):
    username = 'testuser'

    # Mock pwd.getpwnam to return a mock user info
    mock_user_info = MagicMock()
    mock_user_info.pw_uid = 1000
    mock_user_info.pw_gid = 1000
    mock_getpwnam.return_value = mock_user_info

    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / username

        with caplog.at_level(logging.INFO):
            spawner = VirtualEnvSpawner()
            spawner._ensure_user_directory(user_dir, username)

        # Check if the directory was created
        assert user_dir.exists()
        assert user_dir.is_dir()

        # Assert that chown was called with correct parameters
        mock_chown.assert_called_once_with(user_dir, 1000, 1000)

        # Check directory permissions
        st = os.stat(user_dir)
        # Permissions should be 0o750 (rwxr-x---)
        assert (st.st_mode & 0o777) == 0o750

        # Check log messages
        assert f'Getting user info for {username}' in caplog.text
        assert f'Creating user directory for {username}' in caplog.text


@patch('pwd.getpwnam')
def test_ensure_user_directory_user_not_found(mock_getpwnam, caplog):
    username = 'nonexistentuser'

    # Mock pwd.getpwnam to raise KeyError (simulating that the user does not exist)
    mock_getpwnam.side_effect = KeyError

    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / username

        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError, match=f'System user {username} does not exist'):
                spawner = VirtualEnvSpawner()
                spawner._ensure_user_directory(user_dir, username)

        # Check that the directory was not created
        assert not user_dir.exists()

        # Check log messages
        assert f'Getting user info for {username}' in caplog.text


@patch('os.chown')
@patch('os.chmod')
def test_ensure_user_directory_reuse_existing(mock_chown, mock_chmod, caplog):
    username = 'testuser'

    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / username

        # Create the directory ahead of time to simulate that it already exists
        user_dir.mkdir(parents=True, exist_ok=True)

        with caplog.at_level(logging.INFO):
            spawner = VirtualEnvSpawner()
            spawner._ensure_user_directory(user_dir, username)

        # Check that mkdir, chown, and chmod were not called since directory exists
        assert user_dir.exists()
        mock_chown.assert_not_called()
        mock_chmod.assert_not_called()

        # Check log message
        assert f'Reusing user directory for {username}' in caplog.text


def test_ensure_user_jupyter_directory():
    username = 'testuser'

    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / username

        # Create the user directory to simulate the existence of the user directory
        user_dir.mkdir(parents=True, exist_ok=True)

        spawner = VirtualEnvSpawner()
        spawner._ensure_user_jupyter_directory(user_dir)

        # Expected directories
        jupyter_dir = user_dir / '.jupyter'
        jupyter_runtime_dir = jupyter_dir / 'runtime'
        jupyter_data_dir = jupyter_dir / 'data'

        # Check if the directories were created
        assert jupyter_dir.exists()
        assert jupyter_runtime_dir.exists()
        assert jupyter_data_dir.exists()

        # Assert the JUPYTER environment variables are set correctly
        assert spawner.environment['JUPYTER_CONFIG_DIR'] == str(jupyter_dir)
        assert spawner.environment['JUPYTER_RUNTIME_DIR'] == str(jupyter_runtime_dir)
        assert spawner.environment['JUPYTER_DATA_DIR'] == str(jupyter_data_dir)


def test_ensure_user_jupyter_directory_user_dir_does_not_exist():
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / 'nonexistentuser'

        # Ensure the user directory does not exist
        assert not user_dir.exists()

        spawner = VirtualEnvSpawner()

        with pytest.raises(ValueError, match=f'User directory {user_dir} does not exist'):
            spawner._ensure_user_jupyter_directory(user_dir)


@patch('venv.create')
def test_create_virtual_environment(mock_venv_create, caplog, spawner):
    with tempfile.TemporaryDirectory() as temp_dir:
        user_env_dir = Path(temp_dir) / 'venv'

        assert not user_env_dir.exists()
        with caplog.at_level(logging.INFO):
            spawner._ensure_virtual_environment(user_env_dir)

            assert user_env_dir.exists()
            mock_venv_create.assert_called_once_with(
                env_dir=user_env_dir, system_site_packages=True, with_pip=True
            )

        assert f'Creating virtual environment for {spawner.user.name}' in caplog.text


@patch('subprocess.run')
def test_ensure_virtual_environment_raises(mock_run, caplog, spawner):
    with tempfile.TemporaryDirectory() as temp_dir:
        user_env_dir = Path(temp_dir) / 'venv'

        assert not user_env_dir.exists()

        mock_run.side_effect = subprocess.CalledProcessError(1, 'venv')  # Simulate venv creation failure

        with pytest.raises(ValueError, match=f'Failed to create virtual environment for {spawner.user.name}'):
            spawner._ensure_virtual_environment(user_env_dir)


@patch('subprocess.run')
def test_reuse_virtual_environment(mock_run, caplog, spawner):
    with tempfile.TemporaryDirectory() as temp_dir:
        user_env_dir = Path(temp_dir) / 'venv'
        user_env_dir.mkdir()

        assert user_env_dir.exists()

        with caplog.at_level(logging.INFO):
            spawner._ensure_virtual_environment(user_env_dir)

            mock_run.assert_not_called()

            assert f'Reusing virtual environment for {spawner.user.name}' in caplog.text


@patch.dict(os.environ, {
    'PATH': '/usr/local/bin:/usr/bin:/bin',
    'PYTHONPATH': '/usr/local/lib/python3.11/site-packages',
    'JUPYTERHUB_CONFIG_DIR': '/etc/jupyterhub',
    'MINIO_RW_ACCESS_KEY': 'minio_rw_access',
    'MINIO_RW_SECRET_KEY': 'minio_rw_secret',
    'JUPYTERHUB_ADMIN_PASSWORD': 'admin_password',
    'EXISTING_VAR': 'existing_value',
    'OVERWRITE_VAR': 'original_value'
})
def test_configure_environment_non_admin(spawner, caplog):
    user_dir = Path('/home/testuser')
    user_env_dir = Path('/home/testuser/.venv')
    username = 'testuser'

    # Set a variable in the spawner's environment to test overwriting behavior
    spawner.environment['OVERWRITE_VAR'] = 'spawner_value'

    with caplog.at_level(logging.INFO):
        spawner._configure_environment(user_dir, user_env_dir, username)

    # Check that existing environment variables are copied
    assert spawner.environment['EXISTING_VAR'] == 'existing_value'

    # Check that the spawner's existing environment variables are not overwritten
    assert spawner.environment['OVERWRITE_VAR'] == 'spawner_value'

    # Check that new environment variables are set correctly
    assert spawner.environment['HOME'] == str(user_dir)
    assert spawner.environment['PATH'] == f"{user_env_dir}/bin:/usr/local/bin:/usr/bin:/bin"
    assert spawner.environment[
               'PYTHONPATH'] == f"{user_env_dir}/lib/python3.11/site-packages:/usr/local/lib/python3.11/site-packages"
    assert spawner.environment['PYTHONSTARTUP'] == '/etc/jupyterhub/startup.py'
    assert spawner.environment['JUPYTERHUB_USER'] == username

    # Check that the admin credentials are removed for non-admin users
    assert 'MINIO_RW_ACCESS_KEY' not in spawner.environment
    assert 'MINIO_RW_SECRET_KEY' not in spawner.environment
    assert 'JUPYTERHUB_ADMIN_PASSWORD' not in spawner.environment

    assert f"Environment variables for {username}" in caplog.text
    assert str(spawner.environment) in caplog.text
    assert f'Non-admin user detected: {username}. Removing admin credentials.' in caplog.text

@patch.dict(os.environ, {
    'PATH': '/usr/local/bin:/usr/bin:/bin',
    'PYTHONPATH': '/usr/local/lib/python3.11/site-packages',
    'JUPYTERHUB_CONFIG_DIR': '/etc/jupyterhub',
    'MINIO_RW_ACCESS_KEY': 'minio_rw_access',
    'MINIO_RW_SECRET_KEY': 'minio_rw_secret',
})
def test_configure_minio_environment_admin(spawner, caplog):
    spawner.user.admin = True
    user_dir = Path('/home/testadminuser')
    user_env_dir = Path('/home/testuser/.venv')
    username = 'testadminuser'

    with caplog.at_level(logging.INFO):
        spawner._configure_environment(user_dir, user_env_dir, username)

    assert spawner.environment['MINIO_RW_ACCESS_KEY'] == 'minio_rw_access'
    assert spawner.environment['MINIO_ACCESS_KEY'] == 'minio_rw_access'

    assert spawner.environment['MINIO_RW_SECRET_KEY'] == 'minio_rw_secret'
    assert spawner.environment['MINIO_SECRET_KEY'] == 'minio_rw_secret'

    assert f'MinIO read/write user detected: {username}. Setting up minio_rw credentials.' in caplog.text


@patch.dict(os.environ, {
    'PATH': '/usr/local/bin:/usr/bin:/bin',
    'PYTHONPATH': '/usr/local/lib/python3.11/site-packages',
    'JUPYTERHUB_CONFIG_DIR': '/etc/jupyterhub',
    'MINIO_RW_ACCESS_KEY': 'minio_rw_access',
    'MINIO_RW_SECRET_KEY': 'minio_rw_secret',
})
def test_configure_environment_minio_rw_group(spawner, caplog):
    # Mock the user's groups to include the minio_rw group
    mock_group_minio_rw = MagicMock()
    mock_group_minio_rw.name = 'minio_rw'
    spawner.user.groups = [mock_group_minio_rw]

    user_dir = Path('/home/testadminuser')
    user_env_dir = Path('/home/testuser/.venv')
    username = 'testadminuser'

    with caplog.at_level(logging.INFO):
        spawner._configure_environment(user_dir, user_env_dir, username)

    assert spawner.environment['MINIO_RW_ACCESS_KEY'] == 'minio_rw_access'
    assert spawner.environment['MINIO_ACCESS_KEY'] == 'minio_rw_access'

    assert spawner.environment['MINIO_RW_SECRET_KEY'] == 'minio_rw_secret'
    assert spawner.environment['MINIO_SECRET_KEY'] == 'minio_rw_secret'

    assert f'MinIO read/write user detected: {username}. Setting up minio_rw credentials.' in caplog.text


@patch.dict(os.environ, {}, clear=True)  # Clear the environment for the test
def test_configure_environment_missing_pythonpath(spawner):
    os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'
    os.environ['JUPYTERHUB_CONFIG_DIR'] = '/etc/jupyterhub'

    user_dir = Path('/home/testuser')
    user_env_dir = Path('/home/testuser/.venv')
    username = 'testuser'

    spawner._configure_environment(user_dir, user_env_dir, username)

    # Check that PYTHONPATH is set correctly even when it's not in the original environment
    assert f"{user_env_dir}/lib/python3.11/site-packages" == spawner.environment['PYTHONPATH']


@pytest.mark.parametrize("is_admin", [
    True,  # Admin user case
    False  # Non-admin user case
])
def test_configure_notebook_dir(is_admin, spawner, caplog):
    spawner.user.admin = is_admin
    username = 'testuser'
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir) / 'testuser'
        if not is_admin:
            expected_dir = str(user_dir)
        else:
            expected_dir = str(user_dir.parent)

        with caplog.at_level(logging.INFO):
            spawner._configure_notebook_dir(username, user_dir)

        assert spawner.notebook_dir == expected_dir

        if is_admin:
            assert f'Admin user detected: {username}. Setting up admin workspace.' in caplog.text
        else:
            assert f'Non-admin user detected: {username}. Setting up user-specific workspace.' in caplog.text
