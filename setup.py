#!/usr/bin/env python

import os
from setuptools import setup, find_packages


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with open(file_path, encoding="utf-8") as f:
        return f.read()


setup(
    name="pytest-replay",
    version="0.0.0",
    author="Bruno Oliveira",
    author_email="foss@esss.co",
    maintainer="Bruno Oliveira",
    maintainer_email="bruno@esss.com.br",
    license="MIT",
    url="https://github.com/ESSS/pytest-replay",
    description="Saves previous test runs and allow re-execute previous pytest runs "
    "to reproduce crashes or flaky tests",
    long_description=read("README.rst"),
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["pytest>=3.0.0"],
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["replay = pytest_replay"]},
)
