from setuptools import setup, find_packages

# Use a context manager for safely reading the long description
with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="XTB",
    version="1.0.0",
    author="AustrianTradingMachine",
    author_email="",
    description="A wrapper for the XTB API",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/AustrianTradingMachine/XTB",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'socket',
        'ssl',
        'time',
        'select',
        'json',
        're',
        'threading',
        'logging',
    ],
)