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

# https://docs.python.org/3.11/distutils/apiref.html
from setuptools.command.build_py import build_py
from setuptools import setup, find_packages
from pathlib import Path
import shutil


class CustomBuildPy(build_py):
    def run(self):
        source_config_path = Path(__file__).parent / 'user.ini'
        
        target_config_dir = Path.home() / '.xwrpr'
        target_config_path = target_config_dir / 'user.ini'
        
        target_config_dir.mkdir(parents=True, exist_ok=True)
        
        if not target_config_path.exists():
            shutil.copy2(source_config_path, target_config_path)

        # Run the standard install process
        build_py.run(self)


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    long_description=long_description,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        'xwrpr': ['user.ini','src/xwrpr/api.ini']
    },
    cmdclass={
        'build_py': CustomBuildPy,
        },
)