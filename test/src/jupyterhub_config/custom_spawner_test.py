import subprocess
import unittest
from subprocess import CalledProcessError
from unittest.mock import patch, MagicMock

import pytest

from jupyterhub_config.custom_spawner import VirtualEnvSpawner


@pytest.fixture
def mock_spawner():
    spawner = VirtualEnvSpawner()
    spawner.log = MagicMock()  # Mock the logger
    return spawner


# Test when the user already exists
@patch('subprocess.run')
def test_ensure_system_user_already_exists(mock_run, mock_spawner):
    # Mock 'id' command to simulate user already exists
    mock_run.return_value.returncode = 0

    username = 'testuser'
    mock_spawner._ensure_system_user(username)

    mock_spawner.log.info.assert_called_once_with(f'User {username} already exists')
    mock_run.assert_called_once_with(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# Test when the group and user need to be created
@patch('subprocess.run')
def test_ensure_system_user_create_group_and_user(mock_run, mock_spawner):
    # Define side_effect to simulate user does not exist, group does not exist, and then successful creation
    mock_run.side_effect = [
        MagicMock(returncode=1),  # 'id' command: User does not exist
        MagicMock(returncode=2),  # 'getent' command: Group does not exist
        MagicMock(returncode=0),  # 'groupadd' command: Group created successfully
        MagicMock(returncode=0)  # 'useradd' command: User created successfully
    ]

    username = 'testuser'
    group = 'testgroup'
    mock_spawner._ensure_system_user(username, group)

    expected_calls = [
        unittest.mock.call(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        unittest.mock.call(['getent', 'group', group], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        unittest.mock.call(['sudo', 'groupadd', group], check=True),
        unittest.mock.call(['sudo', 'useradd', '-r', '-g', group, username], check=True)
    ]

    # Check that the expected calls were made in order
    mock_run.assert_has_calls(expected_calls, any_order=False)


# Test when the user is created without a group
@patch('subprocess.run')
def test_ensure_system_user_create_user_without_group(mock_run, mock_spawner):
    # Mock the 'id' command to simulate user does not exist
    mock_run.side_effect = [
        MagicMock(returncode=1),  # User does not exist
        MagicMock(returncode=0)  # User created successfully
    ]

    username = 'testuser'
    mock_spawner._ensure_system_user(username)

    mock_spawner.log.info.assert_called_once_with(f'Creating system user: {username}')
    expected_calls = [
        unittest.mock.call(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        unittest.mock.call(['sudo', 'useradd', '-r', username], check=True)
    ]

    mock_run.assert_has_calls(expected_calls, any_order=False)


# Test subprocess.CalledProcessError is handled correctly
@patch('subprocess.run')
def test_ensure_system_user_error(mock_run, mock_spawner):
    # Mock the 'id' command to simulate user does not exist
    # Mock 'useradd' command to raise CalledProcessError
    mock_run.side_effect = [
        MagicMock(returncode=1),
        CalledProcessError(1, 'useradd')
    ]

    with pytest.raises(ValueError, match="Failed to create system user"):
        mock_spawner._ensure_system_user('testuser')

    expected_calls = [
        unittest.mock.call(['id', 'testuser'], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        unittest.mock.call(['sudo', 'useradd', '-r', 'testuser'], check=True)
    ]

    mock_run.assert_has_calls(expected_calls, any_order=False)
