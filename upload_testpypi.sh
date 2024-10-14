#!/bin/bash

# Description: This script is used to build and upload the package to PyPi
# The script will prompt for the PyPi token
read -sp "Enter your TestPyPI token: " token && echo -e "\n[testpypi]\nusername = __token__\npassword = $token" > $HOME/.pypirc

# Check if twine is installed
if ! python -c "import twine" &> /dev/null; then
  echo "Error: 'twine' is not installed. Please install it with 'pip install twine'."
  exit 1
else
  echo "'twine' is installed."
fi

python3 -m twine upload --repository testpypi dist/*

python3 -m pip install --index-url https://test.pypi.org/simple/ --upgrade xwrpr