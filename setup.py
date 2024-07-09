from setuptools import setup, find_packages
from install_home import CustomInstall
from pathlib import Path

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
