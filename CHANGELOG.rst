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
