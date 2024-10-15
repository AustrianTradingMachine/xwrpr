# Dockerfile for Python 3.9 development environment
#
#------------------------------------------------
# Select the base image
#------------------------------------------------
#
# Use the official Debian image as the base image
# https://hub.docker.com/_/debian
# Debian Bullseye (11) used which also has python 3.9 as standard version
FROM debian:11
#
#------------------------------------------------
# Set the metadata
#------------------------------------------------
#
LABEL name = "debian11_python3.9"
LABEL description = "Dockerfile for python 3.9 development environment"
#
#------------------------------------------------
# Define arguments for the base image
#------------------------------------------------
#
# Define the architecture argument
ARG TARGETARCH
#
# Prevent dialog during apt install
ARG DEBIAN_FRONTEND noninteractive
#
# Set the language environment variable
ENV LANG = C.UTF-8
ENV LC_ALL = C.UTF-8
#
#------------------------------------------------
# Set the working directory for software installation
#------------------------------------------------
#
# Create a directory for the installation
RUN mkdir -p /opt
#
# Set the working directory
WORKDIR /opt
#
#------------------------------------------------
# Install apt packages
#------------------------------------------------
#
# Update the repository sources list
# Clean up the apt-get cache
RUN apt-get update --fix-missing && \
    apt-get install -y -q --no-install-recommends \
        software-properties-common \
        apt-transport-https \
        build-essential \
        ca-certificates \
        iproute2 \
        wget \
        sudo \
        curl \
        zip \
        unzip \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
#
#------------------------------------------------
# Install Python 3.9
#------------------------------------------------
#
# Install Python 3.9 with pip, venv, dev, setuptools, wheel
# Clean up the apt-get cache
RUN apt-get update --fix-missing && \
    apt-get install -y -q --no-install-recommends \
        python3 \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-wheel \
        python3-setuptools && \ 
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
#
#------------------------------------------------
# Set the working directory for development
#------------------------------------------------
#
# Create a directory for the app
RUN mkdir -p /workspaces
#
# Set the working directory
WORKDIR /workspaces
#
#------------------------------------------------
# Install Python dependencies
#------------------------------------------------
#
# Copy the current directory contents into the container
COPY .. .
#
# Install the reqirements
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_dev.txt
#
# make sure all messages always reach console
ENV PYTHONUNBUFFERED = 1
#
# Set the encoding to UTF-8
ENV PYTHONIOENCODING = UTF-8
#
#------------------------------------------------
# Create a non-root user
#------------------------------------------------
#
# Create a non-root user
RUN groupadd -r developer && useradd -r -g developer -ms /bin/bash developer && \
    mkdir -p /etc/sudoers.d && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/developer
#
# Ensure the /app directory is owned by the non-root user
RUN chown -R developer:developer /workspaces
#
# Switch to the new user
USER developer