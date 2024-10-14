#!/bin/bash

# Check if twine is installed
if ! python -c "import build" &> /dev/null; then
  echo "Error: 'build' is not installed. Please install it with 'pip install build'."
  exit 1
else
  echo "'build' is installed."
fi

# Build the source distribution
python3 -m build --sdist

# Build the wheel
python3 -m build --wheel