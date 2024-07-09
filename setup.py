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
