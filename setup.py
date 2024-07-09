from setuptools import setup, find_packages

# Use a context manager for safely reading the long description
with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

VERSION = '0.1.0'
API = '2.5.0'

setup(
    name="XTBpy",
    version=VERSION,
    api_version=API
    author="Philipp Craighero",
    author_email="",
    description="A wrapper for the XTB API",
    long_description=long_description,
    keywords=['XTB','API''trading','finance','development'],
    url='https://github.com/AustrianTradingMachine/XTBpy',
    packages=find_packages(),
    license="GNU General Public License v3 (GPLv3)",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires='>=3.9',
    install_requires=[
        'pandas'>=2.*,
        'pytz',
        'tzlocal',
    ],
)
