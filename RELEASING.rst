Here are the steps on how to make a new release.

1. Create a ``release-VERSION`` branch from ``upstream/master``.
2. Update ``CHANGELOG.rst``: make sure the ``UNRELEASED`` section covers every
   change since the last tag, and replace ``*UNRELEASED*`` with the release date.
   There is no version to bump: ``setuptools_scm`` derives it from the tag.
3. Push the branch and open a PR.
4. Once all builds pass, push a ``VERSION`` tag on the release commit to
   ``upstream``. This triggers the ``deploy`` workflow, which publishes to PyPI.
5. Once the package is on PyPI, merge the PR using a merge commit (not squash),
   so the tagged commit stays part of ``master``'s history.
