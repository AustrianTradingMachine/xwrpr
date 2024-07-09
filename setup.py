from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

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
    long_description_content_type="text/markdown",
    keywords="XTB,API,trading,finance,development",
    url='https://github.com/AustrianTradingMachine/XTBpy',
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7, <4",
    install_requires=['pandas','pytz','tzlocal'],
    license='GPLv3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
)
