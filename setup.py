#!/usr/bin/env python3

from setuptools import setup
from pathlib import Path

readme = Path("README.md").read_text()


setup(
    name="fakewindowsize",
    packages=["fakewindowsize"],
    version="0.1",
    license="GPL3",
    description="Python3 module to generate realistic browsers window size.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Carlos A. Planchón",
    keywords=["fake", "window", "size"],
    install_requires=[
        "beautifulsoup4",
        "requests"
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3.7",
    ],
)
