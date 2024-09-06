import logging
import subprocess
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch, MagicMock

import pytest

from jupyterhub_config.custom_spawner import VirtualEnvSpawner


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
@patch('pathlib.Path.exists')
@patch('pathlib.Path.mkdir')
@patch('os.chown')
@patch('os.chmod')
def test_ensure_user_directory_with_logging(mock_chmod, mock_chown, mock_mkdir, mock_exists, mock_getpwnam, caplog):
    username = 'testuser'
    user_dir = Path('/home/testuser')

    # Mock directory existence check (directory does not exist)
    mock_exists.return_value = False

    # Mock pwd.getpwnam to return a mock user info
    mock_user_info = MagicMock()
    mock_user_info.pw_uid = 1000
    mock_user_info.pw_gid = 1000
    mock_getpwnam.return_value = mock_user_info

    with caplog.at_level(logging.INFO):
        spawner = VirtualEnvSpawner()
        spawner._ensure_user_directory(user_dir, username)

    # Assert that mkdir, chown, and chmod were called with correct parameters
    mock_mkdir.assert_called_once_with(parents=True)
    mock_chown.assert_called_once_with(user_dir, 1000, 1000)
    mock_chmod.assert_called_once_with(user_dir, 0o750)

    assert f'Creating user directory for {username}' in caplog.text


@patch('os.chown')
@patch('os.chmod')
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
def test_ensure_user_directory_reuse_existing(mock_exists, mock_mkdir, mock_chown, mock_chmod, caplog):
    username = 'testuser'
    user_dir = Path('/home/testuser')

    # Mock directory existence check (directory already exists)
    mock_exists.return_value = True

    with caplog.at_level(logging.INFO):
        spawner = VirtualEnvSpawner()
        spawner._ensure_user_directory(user_dir, username)

    # Assert that mkdir was not called since directory already exists
    mock_mkdir.assert_not_called()

    # Assert that chown and chmod were not called since directory already exists
    mock_chown.assert_not_called()
    mock_chmod.assert_not_called()

    # Assert that the correct log message was created
    assert f'Reusing user directory for {username}' in caplog.text


@patch('pathlib.Path.mkdir')
def test_ensure_user_jupyter_directory(mock_mkdir):
    user_dir = Path('/home/testuser')

    spawner = VirtualEnvSpawner()
    spawner._ensure_user_jupyter_directory(user_dir)

    # Assert that mkdir was called with the correct parameters
    expected_calls = [
        unittest.mock.call(parents=True, exist_ok=True),  # .jupyter
        unittest.mock.call(parents=True, exist_ok=True),  # .jupyter/runtime
        unittest.mock.call(parents=True, exist_ok=True)  # .jupyter/data
    ]

    mock_mkdir.assert_has_calls(expected_calls, any_order=False)

    # Expected directories
    jupyter_dir = user_dir / '.jupyter'
    jupyter_runtime_dir = jupyter_dir / 'runtime'
    juputer_data_dir = jupyter_dir / 'data'

    # Assert the JUPYTER environment variables are set correctly
    assert spawner.environment['JUPYTER_CONFIG_DIR'] == str(jupyter_dir)
    assert spawner.environment['JUPYTER_RUNTIME_DIR'] == str(jupyter_runtime_dir)
    assert spawner.environment['JUPYTER_DATA_DIR'] == str(juputer_data_dir)
