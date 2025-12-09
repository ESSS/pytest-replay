import pytest


pytest_plugins = "pytester"


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
