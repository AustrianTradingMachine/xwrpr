#!/bin/bash

################################################################################
# Script to automate common tasks for Python package development and distribution
#
# for execution permission: chmod +x package.sh
# for execution: ./package.sh or bash package.sh
################################################################################

# Set the version you just uploaded
PACKAGE_NAME="xwrpr"
VERSION="1.0.0"

################################################################################

# Helper function to check if the token exists in .pypirc
check_token_exists() {
    local repo=$1
    if grep -q "^\[$repo\]" $HOME/.pypirc 2> /dev/null && grep -q "password = " $HOME/.pypirc 2> /dev/null; then
        echo "Token for $repo already exists."
        return 0
    else
        return 1
    fi
}

# Helper function to write to .pypirc file if the token is missing
write_pypirc() {
    local repo=$1
    if ! check_token_exists $repo; then
        read -sp "Enter your $repo token: " token
        if grep -q "^\[$repo\]" $HOME/.pypirc 2> /dev/null; then
            echo "Adding token to existing $repo section..."
            sed -i "/^\[$repo\]/,/^$/s/password = .*/password = $token/" $HOME/.pypirc
        else
            echo "Adding $repo section to .pypirc..."
            echo -e "\n[$repo]\nusername = __token__\npassword = $token" >> $HOME/.pypirc
        fi
        chmod 600 $HOME/.pypirc
    fi
}

# Function for build task
build() {
    echo "Building the project..."

    # Check if 'build' is installed
    if ! python3 -c "import build" &> /dev/null; then
      echo "Error: 'build' is not installed. Please install it with 'pip install build'."
      exit 1
    fi

    echo "'build' is installed."

    # Clean up old builds
    echo "Cleaning up old build files..."
    rm -rf dist/*

    # Build source distribution and wheel
    python3 -m build --sdist --wheel
}

# Function for development task
development() {
    echo "Running development actions..."

    # Check if package is build
    if ! find . -type d -name "dist" | grep -q .; then
        echo "Error: No build files found in any directory. Please run the build task first."
        exit 1
    fi

    # Install the package in editable mode
    python3 -m pip install -e .
}

# Function to upload to TestPyPI
upload_to_testpypi() {
    echo "Uploading to TestPyPI..."

    # Write the TestPyPI token to .pypirc if it doesn't exist
    write_pypirc "testpypi"

    # Check if 'twine' is installed
    if ! python3 -c "import twine" &> /dev/null; then
      echo "Error: 'twine' is not installed. Please install it with 'pip install twine'."
      exit 1
    fi

    echo "'twine' is installed."

    # Upload to TestPyPI
    python3 -m twine upload --repository testpypi dist/*

    # Retry installation from TestPyPI with a short delay
    max_attempts=5
    attempt=1
    while (( attempt <= max_attempts )); do
        echo "Attempting to install $PACKAGE_NAME==$VERSION from TestPyPI (Attempt $attempt/$max_attempts)..."
        python3 -m pip install --index-url https://test.pypi.org/simple/ --upgrade "$PACKAGE_NAME==$VERSION" && break
        echo "Package version $VERSION not found yet, retrying in 10 seconds..."
        sleep 10
        attempt=$(( attempt + 1 ))
    done

    if (( attempt > max_attempts )); then
        echo "Failed to install $PACKAGE_NAME==$VERSION after $max_attempts attempts."
        exit 1
    fi
}

# Function to upload to PyPI
upload_to_pypi() {
    echo "Uploading to PyPI..."

    # Write the PyPI token to .pypirc if it doesn't exist
    write_pypirc "pypi"

    # Check if 'twine' is installed
    if ! python -c "import twine" &> /dev/null; then
      echo "Error: 'twine' is not installed. Please install it with 'pip install twine'."
      exit 1
    fi

    echo "'twine' is installed."

    # Retry installation from PyPI with a short delay
    max_attempts=5
    attempt=1
    while (( attempt <= max_attempts )); do
        echo "Attempting to install $PACKAGE_NAME==$VERSION from PyPI (Attempt $attempt/$max_attempts)..."
        python3 -m pip install --upgrade "$PACKAGE_NAME==$VERSION" && break
        echo "Package version $VERSION not found yet, retrying in 10 seconds..."
        sleep 10
        attempt=$(( attempt + 1 ))
    done

    if (( attempt > max_attempts )); then
        echo "Failed to install $PACKAGE_NAME==$VERSION after $max_attempts attempts."
        exit 1
    fi
}

# Prompt user for action
echo "Select an action:"
echo "b - Build"
echo "d - Development"
echo "t - Upload to TestPyPI"
echo "p - Upload to PyPI"
read -p "Enter your choice: " action

# Execute the appropriate function based on user input
case "$action" in
    b)
        build
        ;;
    d)
        development
        ;;
    t)
        upload_to_testpypi
        ;;
    p)
        upload_to_pypi
        ;;
    *)
        echo "Invalid choice. Please select a valid action."
        ;;
esac