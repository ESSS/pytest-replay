=============
pytest-replay
=============


.. image:: http://img.shields.io/pypi/v/pytest-replay.svg
    :target: https://pypi.python.org/pypi/pytest-replay

.. image:: https://anaconda.org/conda-forge/pytest-replay/badges/version.svg
    :target: https://anaconda.org/conda-forge/pytest-replay

.. image:: https://travis-ci.org/ESSS/pytest-replay.svg?branch=master
    :target: https://travis-ci.org/ESSS/pytest-replay
    :alt: See Build Status on Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/ESSS/pytest-replay?branch=master
    :target: https://ci.appveyor.com/project/ESSS/pytest-replay/branch/master
    :alt: See Build Status on AppVeyor

.. image:: https://img.shields.io/pypi/pyversions/pytest-replay.svg
    :target: https://pypi.python.org/pypi/pytest-replay

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


Saves previous test runs and allow re-execute previous pytest runs to reproduce crashes or flaky tests

----

This `Pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `Cookiecutter-pytest-plugin`_ template.


Features
--------

This plugin helps to reproduce random or flaky behavior when running tests with xdist. ``pytest-xdist`` executes tests
in a non-predictable order, making it hard to reproduce a behavior seen in CI locally because there's no convenient way
to track which test executed in which worker.

This plugin records the executed node ids by each worker in the directory given by ``--replay-record-dir=<dir>`` flag,
and a ``--replay=<file>`` can be used to re-run the tests from a previous run. For example::

    $ pytest -n auto --replay-record-dir=build/tests/replay

This will generate files with each line being a ``json`` with the following content:
node identification, start time, end time and outcome. It is interesting to note
that usually the node id is repeated twice, that is necessary in case of a test
suddenly crashes we will still have the record of that test started. After the
test finishes, ``pytest-replay`` will add another ``json`` line with the
complete information.
That is also useful to analyze concurrent tests which might have some kind of
race condition and interfere in each other.

For example worker ``gw1`` will generate a file
``.pytest-replay-gw1.txt`` with contents like this::

    {"nodeid": "test_foo.py::test[1]", "start": 0.000}
    {"nodeid": "test_foo.py::test[1]", "start": 0.000, "finish": 1.5, "outcome": "passed"}
    {"nodeid": "test_foo.py::test[3]", "start": 1.5}
    {"nodeid": "test_foo.py::test[3]", "start": 1.5, "finish": 2.5, "outcome": "passed"}
    {"nodeid": "test_foo.py::test[5]", "start": 2.5}
    {"nodeid": "test_foo.py::test[5]", "start": 2.5, "finish": 3.5, "outcome": "passed"}
    {"nodeid": "test_foo.py::test[7]", "start": 3.5}
    {"nodeid": "test_foo.py::test[7]", "start": 3.5, "finish": 4.5, "outcome": "passed"}
    {"nodeid": "test_foo.py::test[8]", "start": 4.5}
    {"nodeid": "test_foo.py::test[8]", "start": 4.5, "finish": 5.5, "outcome": "passed"}


If there is a crash or a flaky failure in the tests of the worker ``gw1``, one can take that file from the CI server and
execute the tests in the same order with::

    $ pytest --replay=.pytest-replay-gw1.txt

Hopefully this will make it easier to reproduce the problem and fix it.


FAQ
~~~

1. ``pytest`` has its own `cache <https://docs.pytest.org/en/latest/cache.html>`_, why use a different mechanism?

   The internal cache saves its data using ``json``, which is not suitable in the advent of a crash because the file
   will not be readable.

2. Shouldn't the ability of selecting tests from a file be part of the ``pytest`` core?

   Sure, but let's try to use this a bit as a separate plugin before proposing
   its inclusion into the core.

Installation
------------

You can install ``pytest-replay`` via `pip`_ from `PyPI`_::

    $ pip install pytest-replay

Or with conda::

    $ conda install -c conda-forge pytest-replay


Contributing
------------

Contributions are very welcome.

Tests can be run with `tox`_ if you are using a native Python installation.

To run tests with `conda <https://conda.io/docs/>`_, first create a virtual environment and execute tests from there
(conda with Python 3.5+ in the root environment)::

    $ python -m venv .env
    $ .env\scripts\activate
    $ pip install -e . pytest-xdist
    $ pytest tests


Releases
~~~~~~~~

Follow these steps to make a new release:

1. Create a new branch ``release-X.Y.Z`` from ``master``;
2. Update ``CHANGELOG.rst``;
3. Open a PR;
4. After it is **green** and **approved**, push a new tag in the format ``X.Y.Z``;

Travis will deploy to PyPI automatically.

Afterwards, update the recipe in `conda-forge/pytest-replay-feedstock <https://github.com/conda-forge/pytest-replay-feedstock>`_.


License
-------

Distributed under the terms of the `MIT`_ license.


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/ESSS/pytest-replay/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
