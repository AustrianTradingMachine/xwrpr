#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    xwrpr - A wrapper for the API of XTB (https://www.xtb.com)
#
#    Copyright (C) 2024  Philipp Craighero
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###########################################################################

from pathlib import Path
import configparser

# Path to the configuration directory
PATH = Path('~/.xwrpr').expanduser() / 'user.ini'

# Cache for configparser object to avoid reloading
_config_cache = None


def _load_config() -> configparser.ConfigParser:
    """
    Loads the configuration file from the user.ini file.

    Returns:
        configparser.ConfigParser: The configuration object.

    Raises:
        FileNotFoundError: If the configuration file is not found.
    """

    # Use the global _config_cache variable
    global _config_cache

    # Define the path to the configuration file
    config_path = PATH

    # Ensure the configuration file exists
    if not config_path.exists():
        raise FileNotFoundError(f'Configuration file not found at {config_path}')
    
    # Load the configuration file
    _config_cache = configparser.ConfigParser()
    _config_cache.read(config_path)
    
    return _config_cache

def _get_config(value: str) -> str:
    """
    Retrieves the value of a configuration key from the user.ini file.

    Args:
        value (str): The key to retrieve the value for.

    Returns:
        str: The value associated with the specified key.

    Raises:
        KeyError: If the key is not found in the configuration file.
        KeyError: If the 'USER' section is not found in the configuration file.
    """

    # Use the global _config_cache variable
    global _config_cache

    # Load the configuration file if not already loaded
    if _config_cache is None:
        config = _load_config()
    else:
        config = _config_cache

    # Ensure the 'USER' section exists
    if 'USER' not in config:
        raise KeyError("'USER' section not found in configuration file")

    try:
        return config['USER'][value]
    except KeyError:
        raise KeyError(f'Key {value} not found in configuration file')

def get_userId(demo: bool) -> str:
    """
    Get the user ID based on the demo flag.

    Parameters:
    - demo (bool): Flag indicating whether the user is in demo mode or not.

    Returns:
    - str: The user ID based on the demo flag.

    Raises:
    - KeyError: If the user ID is not found in the configuration
    """

    try:
        userId = _get_config('DEMO_ID' if demo else 'REAL_ID')
        return userId
    except KeyError as e:
        raise

def get_password() -> str:
    """
    Retrieves the password from the configuration file.

    Returns:
        str: The password stored in the configuration file.

    Raises:
        KeyError: If the password is not found in the configuration
    """

    try:
        password = _get_config('PASSWORD')
        return password
    except KeyError as e:
        raise

def set_path(path: str) -> None:
    """
    Sets the path to the configuration directory.

    Args:
        path (str): The path to the configuration directory.

    Raises:
        ValueError: If the specified path is not a directory.

    Returns:
        None
    """
    
    # Use the global PATH variable
    global PATH

    # Define the new path
    config_path = Path(path).expanduser()

    # Ensure the path is a directory
    if not config_path.exists():
        raise ValueError(f'Invalid path: {path}')
    
    # Clear cache to load new config if path is updated
    global _config_cache
    _config_cache = None

    # Update the global PATH variable
    PATH = config_path