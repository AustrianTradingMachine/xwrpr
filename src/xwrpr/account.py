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

PATH = Path('~/.xwrpr').expanduser()

def _get_config(value: str) -> str:
    """
    Retrieves the value of a configuration key from the user.ini file.

    Args:
        value (str): The key to retrieve the value for.

    Returns:
        str: The value associated with the specified key.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        KeyError: If the specified key is not found in the configuration file.
    """

    dir_path = PATH
    config_path = dir_path / 'user.ini'

    if not config_path.exists():
        raise FileNotFoundError(f'Configuration file not found at {config_path}')
    
    config = configparser.ConfigParser()
    config.read(config_path)

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
    """
    if demo:
        userId = _get_config('DEMO_ID')
    else:
        userId = _get_config('REAL_ID')

    return userId

def get_password() -> str:
    """
    Retrieves the password from the configuration file.

    Returns:
        str: The password stored in the configuration file.
    """
    return _get_config('PASSWORD')

def set_path(path: str) -> None:
    """
    Sets the path to the configuration directory.

    Args:
        path (str): The path to the configuration directory.
    """
    
    config_path = Path(path).expanduser()

    # Check if the path is valid and is a directory
    if not config_path.exists() or not config_path.is_dir():
        raise ValueError(f'Invalid path: {path} (must be a directory)')

    # Set the global PATH variable
    global PATH
    PATH = config_path
