"""Main app module."""
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal

from .controllers.base import Base
from .core.exc import YagerError
from .core.hooks import load_db, log_app_version
from .core.log import YagerLogHandler

# configuration defaults
CONFIG = init_defaults("yager", "yager.data", "yager.reports")


class Yager(App):
    """Yager primary application."""

    class Meta:
        """Application meta-data."""

        label = "yager"

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        exit_on_close = True

        # register functions to hooks
        hooks = [
            ("post_setup", log_app_version),
            ("post_setup", load_db),
        ]

        # load additional framework extensions
        extensions = [
            "colorlog",
            "jinja2",
            "yaml",
        ]

        # configuration handler
        config_handler = "yaml"

        # configuration file suffix
        config_file_suffix = ".yaml"

        # set log handler
        log_handler = "colorlog_custom_format"

        # set the output handler
        output_handler = "jinja2"

        # register handlers
        handlers = [Base, YagerLogHandler]


class YagerTest(TestApp, Yager):
    """A sub-class of Yager that is better suited for testing."""

    class Meta:
        """Test application meta-data."""

        label = "yager"


def main():
    """App entry point."""
    with Yager() as app:
        try:
            app.run()

        except AssertionError as e:
            print("AssertionError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug:
                import traceback

                traceback.print_exc()

        except YagerError as e:
            print("YagerError > %s" % e.args[0])
            app.exit_code = 1

            if app.debug:
                import traceback

                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print("\n%s" % e)
            app.exit_code = 0


if __name__ == "__main__":
    main()
