import json

import pytest


@pytest.fixture
def suite(testdir):
    testdir.makepyfile(
        test_1="""
            def test_foo():
                pass
            def test_bar():
                pass
        """,
        test_2="""
            def test_zz():
                pass
        """,
        test_3="""
            def test_foobar():
                pass
        """,
    )


@pytest.mark.parametrize(
    "extra_option", [(None, ".pytest-replay"), ("--replay-base-name", "NEW-BASE-NAME")]
)
def test_normal_execution(suite, testdir, extra_option, monkeypatch):
    """Ensure scripts are created and the tests are executed when using --replay."""

    class MockTime:
        fake_time = 0.0

        @classmethod
        def perf_counter(cls):
            cls.fake_time += 1.0
            return cls.fake_time

    monkeypatch.setattr("pytest_replay.time", MockTime)

    extra_arg, base_name = extra_option
    dir = testdir.tmpdir / "replay"
    options = ["test_1.py", f"--replay-record-dir={dir}"]

    if extra_arg:
        options.append(f"{extra_arg}={base_name}")

    result = testdir.runpytest(*options)

    result.stdout.fnmatch_lines(f"*replay dir: {dir}")

    replay_file = dir / f"{base_name}.txt"
    contents = replay_file.readlines(True)
    contents = [json.loads(line.strip()) for line in contents]
    assert len(contents) == 4
    assert contents[0] == {"nodeid": "test_1.py::test_foo", "start": 1.0}
    assert contents[1] == {
        "nodeid": "test_1.py::test_foo",
        "start": 1.0,
        "finish": 2.0,
        "outcome": "passed",
    }
    assert contents[2] == {"nodeid": "test_1.py::test_bar", "start": 3.0}
    assert contents[3] == {
        "nodeid": "test_1.py::test_bar",
        "start": 3.0,
        "finish": 4.0,
        "outcome": "passed",
    }
    assert result.ret == 0
    result = testdir.runpytest(f"--replay={replay_file}")
    assert result.ret == 0
    result.stdout.fnmatch_lines(["test_1.py*100%*", "*= 2 passed, 2 deselected in *="])


@pytest.mark.parametrize("comment_format", ["#", "//"])
@pytest.mark.parametrize("name_to_comment, deselected", [("foo", 2), ("zz", 1)])
def test_line_comments(suite, testdir, comment_format, name_to_comment, deselected):
    """Check line comments"""

    replay_dir = testdir.tmpdir / "replay"
    result = testdir.runpytest(f"--replay-record-dir={replay_dir}")
    replay_file = replay_dir / ".pytest-replay.txt"

    contents = replay_file.readlines(True)
    contents = [line.strip() for line in contents]
    contents = [
        (comment_format + line) if name_to_comment in line else line
        for line in contents
    ]
    replay_file_commented = replay_dir / ".pytest-replay_commneted.txt"
    replay_file_commented.write_text("\n".join(contents), encoding="utf-8")

    result = testdir.runpytest(f"--replay={replay_file_commented}")
    assert result.ret == 0
    passed = 4 - deselected
    result.stdout.fnmatch_lines([f"*= {passed} passed, {deselected} deselected in *="])


@pytest.mark.parametrize("do_crash", [True, False])
def test_crash(testdir, do_crash):
    testdir.makepyfile(
        test_crash="""
        import os
        def test_crash():
            if {do_crash}:
                os._exit(1)
        def test_normal():
            pass
    """.format(
            do_crash=do_crash
        )
    )
    dir = testdir.tmpdir / "replay"
    result = testdir.runpytest_subprocess(f"--replay-record-dir={dir}")

    contents = (dir / ".pytest-replay.txt").read()
    test_id = "test_crash.py::test_normal"
    if do_crash:
        assert test_id not in contents
        assert result.ret != 0
    else:
        assert test_id in contents
        assert result.ret == 0


def test_xdist(testdir):
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.parametrize('i', range(10))
        def test(i):
            pass
    """
    )
    dir = testdir.tmpdir / "replay"
    procs = 2
    testdir.runpytest_subprocess("-n", str(procs), f"--replay-record-dir={dir}")

    files = dir.listdir()
    assert len(files) == procs
    test_ids = set()
    for f in files:
        test_ids.update({json.loads(x.strip())["nodeid"] for x in f.readlines()})
    expected_ids = {f"test_xdist.py::test[{x}]" for x in range(10)}
    assert test_ids == expected_ids


@pytest.mark.parametrize("reverse", [True, False])
def test_alternate_serial_parallel_does_not_erase_runs(suite, testdir, reverse):
    """xdist and normal runs should not erase each other's files."""
    command_lines = [
        ("-n", "2", "--replay-record-dir=replay"),
        ("--replay-record-dir=replay",),
    ]
    if reverse:
        command_lines.reverse()
    for command_line in command_lines:
        result = testdir.runpytest_subprocess(*command_line)
        assert result.ret == 0
    assert set(x.basename for x in (testdir.tmpdir / "replay").listdir()) == {
        ".pytest-replay.txt",
        ".pytest-replay-gw0.txt",
        ".pytest-replay-gw1.txt",
    }


def test_skip_cleanup_does_not_erase_replay_files(suite, testdir):
    """--replay-skip-cleanup will not erase replay files, appending data on next run."""
    command_lines = [
        ("-n", "2", "--replay-record-dir=replay"),
        ("-n", "2", "--replay-record-dir=replay", "--replay-skip-cleanup"),
    ]

    expected_node_ids = [
        "test_1.py::test_foo",
        "test_1.py::test_foo",
        "test_2.py::test_zz",
        "test_2.py::test_zz",
    ]

    dir = testdir.tmpdir / "replay"
    expected = expected_node_ids[:]
    for command_line in command_lines:
        result = testdir.runpytest_subprocess(*command_line)
        assert result.ret == 0
        assert set(x.basename for x in dir.listdir()) == {
            ".pytest-replay-gw0.txt",
            ".pytest-replay-gw1.txt",
        }

        replay_file = dir / ".pytest-replay-gw0.txt"
        contents = [json.loads(line)["nodeid"] for line in replay_file.readlines()]
        assert contents == expected
        expected.extend(
            expected_node_ids
        )  # Next run will expect same tests appended again.


def test_cwd_changed(testdir):
    """Ensure that the plugin works even if some tests changes cwd."""
    testdir.tmpdir.join("subdir").ensure(dir=1)
    testdir.makepyfile(
        """
        import os
        def test_1():
            os.chdir('subdir')
        def test_2():
            pass
    """
    )
    dir = testdir.tmpdir / "replay"
    result = testdir.runpytest_subprocess("--replay-record-dir={}".format("replay"))
    replay_file = dir / ".pytest-replay.txt"
    contents = {json.loads(line)["nodeid"] for line in replay_file.readlines()}
    expected = {"test_cwd_changed.py::test_1", "test_cwd_changed.py::test_2"}
    assert contents == expected
    assert result.ret == 0
