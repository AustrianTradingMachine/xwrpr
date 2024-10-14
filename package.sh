#!/bin/bash

# Description: This script is used to build and upload the package to PyPi
# The script will prompt for the PyPi token
read -sp "Enter your PyPI token: " token && echo -e "\n[pypi]\nusername = __token__\npassword = $token" > $HOME/.pypirc

# Check if twine is installed
if ! python -c "import build" &> /dev/null; then
  echo "Error: 'build' is not installed. Please install it with 'pip install build'."
  exit 1
else
  echo "'build' is installed."
fi

# Check if twine is installed
if ! python -c "import twine" &> /dev/null; then
  echo "Error: 'twine' is not installed. Please install it with 'pip install twine'."
  exit 1
else
  echo "'twine' is installed."
fi

# Build the source distribution
python3 -m build --sdist

# Build the wheel
python3 -m build --wheel