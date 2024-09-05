import subprocess
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

    mock_spawner.log.info.assert_called_with(f'User {username} already exists')
    mock_run.assert_called_once_with(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# Test when the group and user need to be created
@patch('subprocess.run')
def test_ensure_system_user_create_group_and_user(mock_run, mock_spawner):
    # Mock the 'id' and 'getent' command returncodes
    def mock_run_side_effect(cmd, *args, **kwargs):
        if cmd == ['id', 'testuser']:
            return MagicMock(returncode=1)  # User does not exist
        elif cmd == ['getent', 'group', 'testgroup']:
            return MagicMock(returncode=2)  # Group does not exist
        return MagicMock(returncode=0)  # Successful creation

    mock_run.side_effect = mock_run_side_effect

    username = 'testuser'
    group = 'testgroup'
    mock_spawner._ensure_system_user(username, group)

    mock_spawner.log.info.assert_any_call(f'Creating system user: {username}')
    mock_spawner.log.info.assert_any_call(f'Group {group} does not exist, creating it.')
    mock_run.assert_any_call(['sudo', 'groupadd', group], check=True)
    mock_run.assert_any_call(['sudo', 'useradd', '-r', '-g', group, username], check=True)


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

    mock_spawner.log.info.assert_any_call(f'Creating system user: {username}')
    mock_run.assert_called_with(['sudo', 'useradd', '-r', username], check=True)


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

    mock_run.assert_any_call(['id', 'testuser'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    mock_run.assert_any_call(['sudo', 'useradd', '-r', 'testuser'], check=True)
