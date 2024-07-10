#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    XTBpy, a wrapper for the API of XTB (https://www.xtb.com)
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

import os
from setuptools.command.install import install
from setuptools import setup, find_packages
from pathlib import Path


class CustomInstall(install):
    """
    Custom installation class that extends the functionality of the base `install` class.
    This class creates a custom installation process for the XTBpy package.
    """
    def run(self):
        # Call the superclass run method
        install.run(self)
        
        # Define the configuration directory and file paths
        config_dir = os.path.expanduser('~/.XTBpy')
        config_file_path = os.path.join(config_dir, 'user.cfg')
        
        # Ensure the configuration directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        # Check if the config file already exists to avoid overwriting
        if not os.path.exists(config_file_path):
            with open(config_file_path, 'w') as config_file:
                config_file.write("# Your default configuration\n")


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    long_description=long_description,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        'XTBpy': ['config/user.cfg']
        },
    cmdclass={
        'install': CustomInstall,
    }
)
