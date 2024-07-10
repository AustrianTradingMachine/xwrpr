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

from setuptools.command.install import install
from setuptools import setup, find_packages
from pathlib import Path
import shutil


class CustomInstall(install):
    def run(self):
        # Run the standard install process
        install.run(self)
        
        source_config_path = Path(__file__).parent / 'user.ini'
        
        target_config_dir = Path.home() / '.XTBpy'
        target_config_path = target_config_dir / 'user.ini'
        
        target_config_dir.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_config_path, target_config_path)
        print(f'Configuration file created at {target_config_path}')


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