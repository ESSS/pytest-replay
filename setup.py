#!/usr/bin/env python
import os

from setuptools import find_packages
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with open(file_path, encoding="utf-8") as f:
        return f.read()


setup(
    name="pytest-replay",
    author="ESSS",
    author_email="foss@esss.co",
    license="MIT",
    url="https://github.com/ESSS/pytest-replay",
    description="Saves previous test runs and allow re-execute previous pytest runs "
    "to reproduce crashes or flaky tests",
    long_description=read("README.rst"),
    long_description_content_type="text/x-rst",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["pytest"],
    use_scm_version=True,
    setup_requires=[
        "setuptools_scm",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["replay = pytest_replay"]},
)
