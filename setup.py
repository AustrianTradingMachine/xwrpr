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

# https://docs.python.org/3.9/distutils/apiref.html
from setuptools.command.build_py import build_py
from setuptools import setup, find_packages
from pathlib import Path
import shutil

# Define the path to the package's root directory
this_directory = Path(__file__).parent

class CustomBuildPy(build_py):
    """
    Custom build process for the package.

    Methods:
        run: Run the custom build process for the package.
    """

    def run(self):
        """
        Run the custom build process for the package.

        Returns:
            None

        Raises:
            FileNotFoundError: If the source configuration file does not exist.
            PermissionError: If the target directory cannot be created.
            IOError: If the source configuration file cannot be copied to the target directory.
        """

        try:
            # Define the source path for the user.ini file
            source_config_path = this_directory / 'user.ini'

            # Ensure the source file exists before proceeding
            if not source_config_path.exists():
                raise FileNotFoundError(f"Source configuration file not found: {source_config_path}")
            
            # Define the target path for the user.ini file
            target_config_dir = Path.home() / '.xwrpr'
            target_config_path = target_config_dir / 'user.ini'
            
            # Create the target directory if it does not exist
            try:
                target_config_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise PermissionError(f"Permission denied while creating directory: {target_config_dir}") from e
            
            # Copy the user.ini file to the user's home directory if it does not exist
            if not target_config_path.exists():
                try:
                    shutil.copy2(source_config_path, target_config_path)
                except (PermissionError, OSError) as e:
                    raise IOError(f"Failed to copy {source_config_path} to {target_config_path}") from e
        except Exception as e:
            raise
        finally:
            # Run the standard install process
            build_py.run(self)


# Read the package's long description from the README file
long_description = (this_directory / "README.md").read_text()

setup(
    # Define the location of the packages description
    long_description=long_description,
    # Set the path to the package's root directory
    package_dir={"": "src"},
    # Find all packages in the src directory (including subpackages)
    packages=find_packages(where="src"),
    # Define the package's metadata
    package_data={
        'xwrpr': ['user.ini','src/xwrpr/api.ini']
    },
    # Defin a custom build process
    cmdclass={
        'build_py': CustomBuildPy,
        },
)