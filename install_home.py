import os
import shutil
from setuptools.command.install import install

class CustomInstall(install):
    """
    Custom installation class that extends the functionality of the base `install` class.
    This class creates a custom installation process for the XTBpy package.
    """

    def run(self):
        """
        Run the custom installation process.

        This method ensures that the parent directory exists, copies the default config file to the destination,
        and then calls the standard install process.

        Raises:
            OSError: If there is an error creating the parent directory or copying the config file.
        """
        # Ensure the parent directory exists
        config_dir = os.path.expanduser("~/.XTBpy")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Path to the default config file within the package
        default_config = os.path.join(os.path.dirname(__file__), 'XTBpy', 'user.cfg')
        
        # Destination path
        destination_config = os.path.join(config_dir, 'user.cfg')
        
        # Copy the default config file to the destination
        if not os.path.exists(destination_config):  # To avoid overwriting an existing file
            shutil.copy(default_config, destination_config)
        
        # Call the standard install process
        super().run()