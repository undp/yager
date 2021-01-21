# -*- coding: utf-8 -*-
"""Framework hooks module."""
from sqlite3 import Connection, Cursor, Error, OperationalError, connect
from typing import Dict

from cement import App

from .version import get_version


def load_db(app: App) -> None:
    """Extend app with SQLite3 database.

    Reads data from configured SQLite3 URI.

    Parameters
    ----------
    app
        Cement Framework application object.
    """
    app.log.debug("Extending app object with database connection")

    data_config: Dict[str, str] = app.config.get("yager", "data")
    if data_config:
        db_uri: str = data_config.get("db_uri", "file:/home/user/.yager/data/sqlite.db")

    app.log.debug("Using database at '{}'".format(db_uri))  # noqa: G001

    try:
        db_connection: Connection = connect(db_uri)
    except OperationalError as e:
        app.extend("db_cursor", None)

        app.log.error("OperationalError: {}".format(str(e)))  # noqa: G001

        if app.debug:
            import traceback

            traceback.print_exc()
    else:
        try:
            db_cursor: Cursor = db_connection.cursor()
        except Error as e:
            app.log.error("Error: {}".format(str(e)))  # noqa: G001

            if app.debug:
                import traceback

                traceback.print_exc()
        else:
            app.extend("db_cursor", db_cursor)


def log_app_version(app: App) -> None:
    """Log the version of the app.

    Parameters
    ----------
    app
        Cement Framework application object.
    """
    app.log.info("Yager version {}".format(get_version()))  # noqa: G001
