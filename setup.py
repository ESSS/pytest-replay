#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-replay',
    version='0.0.0',
    author='Bruno Oliveira',
    author_email='bruno@esss.com.br',
    maintainer='Bruno Oliveira',
    maintainer_email='bruno@esss.com.br',
    license='MIT',
    url='https://github.com/ESSS/pytest-replay',
    description='Saves shell scripts that allow re-execute previous pytest '
                'runs to reproduce crashes or flaky tests',
    long_description=read('README.rst'),
    py_modules=['pytest_replay'],
    install_requires=['pytest>=3.0.0'],
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'replay = pytest_replay',
        ],
    },
)
