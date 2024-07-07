from setuptools import setup, find_packages

# Use a context manager for safely reading the long description
with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="XTB",
    version="1.0.0",
    author="Philipp Craighero",
    author_email="",
    description="A wrapper for the XTB API",
    long_description=long_description,
    url="https://github.com/AustrianTradingMachine/XTB",
    download_url='https://github.com/AustrianTradingMachine/XTB.git',
    packages=find_packages(),
    license="The MIT License (MIT)",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires='>=3.6',
    install_requires=[
        'pytz',
        'pandas',
    ],
    test_suite='tests',
)
