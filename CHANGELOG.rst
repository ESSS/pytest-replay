1.4.0 (2021-06-09)
==================

* Introduce new ``--replay-skip-cleanup`` option that skips the cleanup before running the command. This allows to keep previously generated replay files when running new commands.

1.3.0 (2020-12-09)
==================

* Replay files can now contain comments (``#`` or ``//``), to make it easy to comment out tests from them when trying to narrow the tests to find a culprit.


1.2.1 (2020-08-24)
==================

* Add proper support when running with ``xdist`` in a frozen executable.

1.2.0 (2019-11-14)
==================

* Change the format of the output to be able to add more information. The new output has new information such as
  start time, end time, outcome and the node identification, all these data is represented by each line being a ``json``
  format.

1.1.0 (2019-11-11)
==================

* Introduce new ``--replay-base-name`` option that lets users configure a different name of the replay file. Defaults to ``.pytest-replay``.

1.0.0
=====

* Drop support for Python 2.

0.2.2
=====

* Normal runs and ``xdist`` runs no longer clean up each other's files.

0.2.1
=====

* Fix crash ``IOError`` when tests changed the current working directory in the middle
  of the testing session.

0.2.0
=====

* Replace the shell scripts by plain text files and add new
  ``--replay`` flag which accepts the generated files to run the tests.

0.1.1
=====

* Escape node ids in the generated shell scripts.

0.1.0
=====

* Initial release.
