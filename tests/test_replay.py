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


def test_normal_execution(suite, testdir):
    """Ensure scripts are created and the tests are executed when using --replay."""
    dir = testdir.tmpdir / 'replay'
    result = testdir.runpytest('test_1.py', '--replay-record-dir={}'.format(dir))

    result.stdout.fnmatch_lines('*replay dir: {}'.format(dir))

    replay_file = dir / '.pytest-replay.txt'
    contents = replay_file.readlines(True)
    expected = [
        'test_1.py::test_foo\n',
        'test_1.py::test_bar\n',
    ]
    assert contents == expected
    assert result.ret == 0

    result = testdir.runpytest('--replay={}'.format(replay_file))
    assert result.ret == 0
    result.stdout.fnmatch_lines([
        'test_1.py*100%*',
        '*= 2 passed, 2 deselected in *=',
    ])


@pytest.mark.parametrize('do_crash', [True, False])
def test_crash(testdir, do_crash):
    testdir.makepyfile(test_crash="""
        import os
        def test_crash():
            if {do_crash}:
                os._exit(1)
        def test_normal():
            pass
    """.format(do_crash=do_crash))
    dir = testdir.tmpdir / 'replay'
    result = testdir.runpytest_subprocess('--replay-record-dir={}'.format(dir))

    contents = (dir / '.pytest-replay.txt').read()
    test_id = 'test_crash.py::test_normal'
    if do_crash:
        assert test_id not in contents
        assert result.ret != 0
    else:
        assert test_id in contents
        assert result.ret == 0


def test_xdist(testdir):
    testdir.makepyfile("""
        import pytest
        @pytest.mark.parametrize('i', range(10))
        def test(i):
            pass
    """)
    dir = testdir.tmpdir / 'replay'
    procs = 2
    testdir.runpytest_subprocess('-n', procs, '--replay-record-dir={}'.format(dir))

    files = dir.listdir()
    assert len(files) == procs
    test_ids = []
    for f in files:
        test_ids.extend(x.strip() for x in f.readlines())
    expected_ids = ['test_xdist.py::test[{}]'.format(x) for x in range(10)]
    assert sorted(test_ids) == sorted(expected_ids)
