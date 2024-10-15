#!/bin/bash

################################################################################
# Script to automate the filling of the credentials in the user.ini file
#
# for execution permission: chmod +x credentials.sh
# for execution: ./credentials.sh or bash credentials.sh
################################################################################

# Define the path to the user.ini file
USER_INI="$HOME/.xwrpr/user.ini"

# Create the directory if it doesn't exist
mkdir -p "$HOME/.xwrpr"

# Prompt the user for their XTB account details
echo "###########################################################################"
echo "#                                                                         #"
echo "#    xwrpr - A wrapper for the API of XTB (https://www.xtb.com)         #"
echo "#                                                                         #"
echo "#    Copyright (C) 2024  Philipp Craighero                                #"
echo "#                                                                         #"
echo "#    This program is free software: you can redistribute it and/or modify  #"
echo "#    it under the terms of the GNU General Public License as published by  #"
echo "#    the Free Software Foundation, either version 3 of the License, or     #"
echo "#    (at your option) any later version.                                   #"
echo "#                                                                         #"
echo "#    This program is distributed in the hope that it will be useful,       #"
echo "#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #"
echo "#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #"
echo "#    GNU General Public License for more details.                         #"
echo "#                                                                         #"
echo "#    You should have received a copy of the GNU General Public License     #"
echo "#    along with this program. If not, see <https://www.gnu.org/licenses/>.#"
echo "#                                                                         #"
echo "###########################################################################"
echo ""
echo "[USER]"
echo ""
echo "###########################################################################"
echo "#                                                                         #"
echo "#    replace the default values with your data of your XTB account        #"
echo "#                                                                         #"
echo "#    REAL_ID: your real account ID                                         #"
echo "#    DEMO_ID: your demo account ID                                         #"
echo "#    PASSWORD: your password                                               #"
echo "#                                                                         #"
echo "#    you can find your account ID in the XTB platform                     #"
echo "#                                                                         #"
echo "#    make sure you are the only one who can access this file              #"
echo "#                                                                         #"
echo "###########################################################################"

# Read user input
read -p "Enter your REAL_ID: " REAL_ID
read -p "Enter your DEMO_ID: " DEMO_ID
read -s -p "Enter your PASSWORD: " PASSWORD
echo ""  # New line for better formatting

# Create or overwrite the user.ini file
{
    echo "REAL_ID = $REAL_ID"
    echo "DEMO_ID = $DEMO_ID"
    echo "PASSWORD = $PASSWORD"
} > "$USER_INI"

# Set permissions to restrict access to the file
chmod 600 "$USER_INI"

echo "Configuration saved to $USER_INI"
