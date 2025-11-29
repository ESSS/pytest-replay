import re

import pytest


@pytest.fixture
def suite_replay_xdist(suite, testdir):
    out_dir = testdir.tmpdir / "replay_xdist"
    out_dir.mkdir()
    file_gw0 = out_dir / "replay_gw0.txt"
    file_gw1 = out_dir / "replay_gw1.txt"

    file_gw0.write_text(
        """{"nodeid": "test_1.py::test_foo", "start": 0.5}
    {"nodeid": "test_1.py::test_foo", "start": 0.5, "finish": 1.0, "outcome": "passed"}
    {"nodeid": "test_1.py::test_bar", "start": 1.0}
    {"nodeid": "test_1.py::test_bar", "start": 1.0, "finish": 1.5, "outcome": "passed"}""",
        encoding="utf-8",
    )
    file_gw1.write_text(
        """{"nodeid": "test_2.py::test_zz", "start": 0.5}
    {"nodeid": "test_2.py::test_zz", "start": 0.5, "finish": 1.0, "outcome": "passed"}
    {"nodeid": "test_3.py::test_foobar", "start": 1.0}
    {"nodeid": "test_3.py::test_foobar", "start": 1.0, "finish": 1.5, "outcome": "passed"}""",
        encoding="utf-8",
    )
    yield file_gw0, file_gw1


def test_run_multiple_files_with_xdist(testdir, suite_replay_xdist):
    file_gw0, file_gw1 = suite_replay_xdist
    result = testdir.runpytest(
        "--replay",
        str(file_gw0),
        str(file_gw1),
        "-v",
    )
    assert result.ret == 0
    assert result.parseoutcomes() == {"passed": 4}
    stdout = result.stdout.str()
    assert "created: 2/2 workers" in stdout
    assert re.search(r"\[gw1\] .* PASSED test_2\.py::test_zz", stdout)
    assert re.search(r"\[gw0\] .* PASSED test_1\.py::test_foo", stdout)
    assert re.search(r"\[gw1\] .* PASSED test_3\.py::test_foobar", stdout)
    assert re.search(r"\[gw0\] .* PASSED test_1\.py::test_bar", stdout)


@pytest.mark.parametrize(
    "extra_args",
    [
        ["-n", "2"],
        ["-n=2"],
        ["--dist", "loadgroup"],
        ["--dist=loadgroup"],
        ["--maxprocesses", "2"],
        ["--maxprocesses=2"],
        ["--numprocesses", "2"],
        ["--numprocesses=2"],
        ["-n", "2", "--dist", "loadgroup"],
    ],
)
def test_exception_multiple_replay_files(testdir, suite_replay_xdist, extra_args):
    file_gw0, file_gw1 = suite_replay_xdist
    result = testdir.runpytest("--replay", str(file_gw0), str(file_gw1), *extra_args)
    assert result.ret == 4
