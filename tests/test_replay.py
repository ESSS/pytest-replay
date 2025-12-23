import itertools as it
import json
import re
from pathlib import Path

import pytest


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
    assert {x.basename for x in (testdir.tmpdir / "replay").listdir()} == {
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
        "test_1.py::test_bar",
        "test_1.py::test_bar",
    ]

    dir = testdir.tmpdir / "replay"
    expected = expected_node_ids[:]
    for command_line in command_lines:
        result = testdir.runpytest_subprocess(*command_line)
        assert result.ret == 0
        assert {x.basename for x in dir.listdir()} == {
            ".pytest-replay-gw0.txt",
            ".pytest-replay-gw1.txt",
        }

        replay_file = dir / ".pytest-replay-gw0.txt"
        contents = [json.loads(line)["nodeid"] for line in replay_file.readlines()]
        assert contents == expected
        # Next run will expect same tests appended again.
        expected.extend(expected_node_ids)


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


@pytest.mark.usefixtures("suite")
def test_execution_different_order(testdir):
    """Ensure tests execute in the order defined by the JSON file, not collection (#52)."""
    dir = testdir.tmpdir / "replay"
    options = [f"--replay-record-dir={dir}"]
    result = testdir.runpytest(*options)

    replay_file = dir / ".pytest-replay.txt"

    with replay_file.open("r+") as f:
        content = f.readlines()

        # pairwise shuffle of replay file
        pairs = [(content[i], content[i + 1]) for i in range(0, len(content), 2)]
        pairs = [pairs[2], pairs[0], pairs[3], pairs[1]]
        content = list(it.chain.from_iterable(pairs))

        f.seek(0)
        f.writelines(content)

    result = testdir.runpytest(f"--replay={replay_file}", "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(
        [
            "test_2.py::test_zz*25%*",
            "test_1.py::test_foo*50%*",
            "test_3.py::test_foobar*75%*",
            "test_1.py::test_bar*100%*",
        ],
        consecutive=True,
    )


@pytest.mark.usefixtures("suite")
def test_filter_out_tests_not_in_file(testdir):
    """Tests not found in the JSON file should not run."""
    dir = testdir.tmpdir / "replay"
    options = [f"--replay-record-dir={dir}", "-k", "foo"]
    result = testdir.runpytest(*options)

    replay_file = dir / ".pytest-replay.txt"

    result = testdir.runpytest(f"--replay={replay_file}", "-v")
    assert result.ret == 0
    result.stdout.fnmatch_lines(
        [
            "test_1.py::test_foo*50%*",
            "test_3.py::test_foobar*100%*",
        ],
        consecutive=True,
    )


def test_metadata(pytester, tmp_path):
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def seed(replay_metadata):
            assert replay_metadata.metadata == {}
            replay_metadata.metadata["seed"] = seed = 1234
            return seed

        def test_foo(seed):
            assert seed == 1234
        """
    )
    dir = tmp_path / "replay"
    result = pytester.runpytest(f"--replay-record-dir={dir}")
    assert result.ret == 0

    # Rewrite the fixture to always returns the metadata, as written previously.
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def seed(replay_metadata):
            return replay_metadata.metadata["seed"]

        def test_foo(seed):
            assert seed == 1234
        """
    )
    result = pytester.runpytest(f"--replay={dir / '.pytest-replay.txt'}")
    assert result.ret == 0


def test_replay_file_outcome_is_correct(testdir):
    """Tests that the outcomes in the replay file are correct."""
    testdir.makepyfile(
        test_module="""
        import pytest

        def test_success():
            pass

        def test_failure():
            assert False

        @pytest.fixture
        def failing_teardown_fixture():
            yield
            assert False

        def test_failure_fixture_teardown(failing_teardown_fixture):
            assert True

        @pytest.fixture
        def failing_setup_fixture():
            assert False

        def test_failure_fixture_setup(failing_setup_fixture):
            assert True
    """
    )
    dir = testdir.tmpdir / "replay"
    result = testdir.runpytest_subprocess(f"--replay-record-dir={dir}")
    assert result.ret != 0

    contents = [json.loads(s) for s in (dir / ".pytest-replay.txt").read().splitlines()]
    outcomes = {r["nodeid"]: r["outcome"] for r in contents if "outcome" in r}
    assert outcomes == {
        "test_module.py::test_success": "passed",
        "test_module.py::test_failure": "failed",
        "test_module.py::test_failure_fixture_teardown": "failed",
        "test_module.py::test_failure_fixture_setup": "failed",
    }


def test_replay_file_outcome_is_correct_xdist(testdir):
    """Tests that the outcomes in the replay file are correct when running in parallel."""
    testdir.makepyfile(
        test_module="""
        import pytest

        @pytest.mark.parametrize('i', range(10))
        def test_val(i):
            assert i < 5
    """
    )
    dir = testdir.tmpdir / "replay"
    procs = 2
    result = testdir.runpytest_subprocess(f"--replay-record-dir={dir}", f"-n {procs}")
    assert result.ret != 0

    contents = [
        s
        for n in range(procs)
        for s in (dir / f".pytest-replay-gw{n}.txt").read().splitlines()
    ]
    pattern = re.compile(r"test_val\[(\d+)\]")
    for content in contents:
        parsed = json.loads(content)
        if "outcome" not in parsed:
            continue

        i = int(pattern.search(parsed["nodeid"]).group(1))
        if i < 5:
            assert parsed["outcome"] == "passed", i
        else:
            assert parsed["outcome"] == "failed", i


def test_outcomes_in_replay_file(testdir):
    """Tests that checks how the outcomes are handled in the report hook when the various
    phases yield failure or skipped."""
    testdir.makepyfile(
        test_module="""
        import pytest

        @pytest.fixture()
        def skip_setup():
            pytest.skip("skipping")
            yield

        @pytest.fixture()
        def skip_teardown():
            yield
            pytest.skip("skipping")

        @pytest.fixture()
        def fail_setup():
            assert False

        @pytest.fixture()
        def fail_teardown():
            yield
            assert False

        def test_skip_fail(skip_setup, fail_teardown):
            pass

        def test_fail_skip(fail_setup, skip_teardown):
            pass

        def test_skip_setup(skip_setup):
            pass

        def test_skip_teardown(skip_teardown):
            pass

        def test_test_fail_skip_teardown(skip_teardown):
            assert False
    """
    )
    dir = testdir.tmpdir / "replay"
    testdir.runpytest_subprocess(f"--replay-record-dir={dir}")

    contents = [json.loads(s) for s in (dir / ".pytest-replay.txt").read().splitlines()]
    outcomes = {r["nodeid"]: r["outcome"] for r in contents if "outcome" in r}
    assert outcomes == {
        "test_module.py::test_skip_fail": "skipped",
        "test_module.py::test_fail_skip": "failed",
        "test_module.py::test_skip_setup": "skipped",
        "test_module.py::test_skip_teardown": "skipped",
        "test_module.py::test_test_fail_skip_teardown": "failed",
    }


@pytest.mark.usefixtures("suite")
def test_empty_or_blank_lines(testdir):
    """Empty or blank line in replay files should be ignored."""
    dir = testdir.tmpdir / "replay"
    options = [f"--replay-record-dir={dir}"]
    result = testdir.runpytest(*options)
    replay_file: Path = dir / ".pytest-replay.txt"

    with replay_file.open("r+") as f:
        content = f.readlines()

        # Add empty line
        content.insert(1, "\n")
        # Add blank line
        content.insert(1, "    \n")
        # Add empty line
        content.append("\n")
        # Add mixed blank line
        content.append("\t \n")
        f.seek(0)
        f.writelines(content)

    result = testdir.runpytest(f"--replay={replay_file}", "-v")
    assert result.ret == 0


def test_custom_command_line_options(testdir):
    """Custom command-line options from other plugins should not break pytest-replay (#105)."""
    testdir.makeconftest(
        """
        def pytest_addoption(parser):
            parser.addoption(
                '--custom-option',
                action='store_true',
                default=False,
                help='A custom command-line option'
            )
        """
    )
    testdir.makepyfile(
        """
        def test_with_custom_option(request):
            assert request.config.getoption('custom_option') is True
        """
    )
    record_dir = testdir.tmpdir / "replay"
    result = testdir.runpytest(f"--replay-record-dir={record_dir}", "--custom-option")
    assert result.ret == 0

    replay_file = record_dir / ".pytest-replay.txt"
    result = testdir.runpytest(f"--replay={replay_file}", "--custom-option")
    assert result.ret == 0
