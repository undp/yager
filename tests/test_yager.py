"""Module defines app test cases."""
from yager.main import YagerTest


def test_yager():
    """Test without any subcommands or arguments."""
    with YagerTest() as app:
        app.run()
        assert app.exit_code == 0  # noqa: S101


def test_yager_debug():
    """Test that debug mode is functional."""
    argv = ["--debug"]
    with YagerTest(argv=argv) as app:
        app.run()
        assert app.debug is True  # noqa: S101
