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

userid_real = os.getenv('XTB_USERNAME')
userid_demo = os.getenv('XTB_USERNAME_DEMO')
password = os.getenv('XTB_PASSWORD')

env_vars = [userid_real, userid_demo, password]

if None in env_vars or "" in env_vars:
    raise ValueError("Please set the environment variables XTB_USERNAME, XTB_USERNAME_DEMO and XTB_PASSWORD")
