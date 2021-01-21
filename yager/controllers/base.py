"""Base app controller module."""
from csv import DictReader
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from sqlite3 import Cursor, Error, OperationalError
from string import Formatter
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, parse as xml_parse  # noqa: S405

from cement import Controller, ex
from cement.utils.version import get_version_banner

from jinja2 import Environment, FileSystemLoader

from tabulate import tabulate

from ..core.version import get_version

VERSION_BANNER = """
Yager %s
%s
""" % (
    get_version(),
    get_version_banner(),
)


class Base(Controller):
    """ Class implementing base app controller."""

    class Meta:
        """Controller meta-data."""

        label = "base"

        description = "Yet Another GEneric Reporter tool for parsing of XML data into an SQLite database and subsequent universal reporting based on SQL queries and Jinja2 templates."  # noqa: E501
        epilog = "Usage: yager {sub-command} {options}"

        arguments = [
            (["-v", "--version"], {"action": "version", "version": VERSION_BANNER}),
        ]

    def _query_db(self, sql_query: str) -> Optional[Cursor]:
        """Query database.

        Helper to execute `sql_query` against the app database.

        Parameters
        ----------
        sql_query
            SQLite3 query to be executed.

        Returns
        -------
        :obj:`~typing.Optional` [:obj:`~sqlite3.Cursor`]
            If successful, returns :obj:`~sqlite3.Cursor` with results.
            Otherwise returns ``None``.
        """
        # Stop processing, if DB is not available
        if self.app.db_cursor is None:
            self.app.log.error("No database connection")
            return

        self.app.log.debug("Executing query '{}'".format(sql_query))

        response: Optional[Cursor] = None

        try:
            response = self.app.db_cursor.execute(sql_query)

        except OperationalError as e:
            self.app.log.error("sqlite3.OperationalError: {}".format(str(e)))

        except Error as e:
            self.app.log.error("Unexpected Error: {}".format(str(e)))

            if self.app.debug:
                import traceback

                traceback.print_exc()

        else:
            return response

    @ex(
        help="execute a query against database",
        arguments=[
            (
                ["--output", "-o"],
                {
                    "help": "defines how to format the output (choose from 'csv' or 'table'; default: 'table')",  # noqa: E501
                    "action": "store",
                    "metavar": "FORMAT",
                    "required": False,
                    "dest": "output_format",
                    "choices": ["csv", "table"],
                    "default": "table",
                },
            ),
            (["sql_query"], {"help": "query to be executed", "metavar": "QUERY"},),
        ],
    )
    def query(self) -> None:
        """Execute a query against the app database."""
        # Stop processing, if DB is not available
        if self.app.db_cursor is None:
            self.app.log.error("No database connection")
            return

        # get required params from CLI
        out_format: str = self.app.pargs.output_format
        sql_query: str = self.app.pargs.sql_query

        # init local vars
        sql_header: List[str] = []
        sql_response: Optional[Cursor] = None
        sql_data: List[str] = []

        sql_response = self._query_db(sql_query)
        if sql_response:
            sql_header = list(map(lambda x: x[0], self.app.db_cursor.description))
            sql_data = sql_response.fetchall()

            if out_format == "table":
                print(tabulate(sql_data, headers=sql_header))

            elif out_format == "csv":
                self.app.render(
                    {"records": sql_data, "header": sql_header}, "output_csv.j2",
                )

            else:
                self.app.log.error("Unknown output format {}".format(out_format))

    @ex(
        help="execute a pre-configured report",
        arguments=[
            (
                ["--param", "-p"],
                {
                    "help": "NAME=VALUE pair defining a global query parameter \
                        to be used for each query in the template \
                        (could be repetated)",
                    "action": "append",
                    "metavar": "PARAM",
                    "dest": "param_list",
                },
            ),
            (["report_name"], {"help": "report to be executed", "metavar": "NAME"},),
        ],
    )
    def report(self) -> None:
        """Execute a pre-configured report."""
        # Stop processing, if DB is not available
        if self.app.db_cursor is None:
            self.app.log.error("No database connection")
            return

        # get required params from app config
        all_report_configs: List[Dict] = self.app.config.get("yager", "reports")
        all_report_names: List[str] = list(map(lambda x: x["name"], all_report_configs))

        # get required params from CLI
        query_params_list: List = self.app.pargs.param_list

        report_name: str = self.app.pargs.report_name
        if report_name not in all_report_names:
            self.app.log.error("Unknown report name '{}'".format(report_name))
            self.app.log.debug(
                "Available reports are: '{}'".format("','".join(all_report_names))
            )

            return

        # init local vars
        report_config: Dict = all_report_configs[all_report_names.index(report_name)]
        template_params: List = report_config["template_params"]
        template_input_data: Dict = {}

        self.app.log.info(
            "Executing report template '{}'".format(report_config["name"])
        )

        for param in template_params:
            # expand possible query parameters
            sql_query_parametrized: str = param["query"]
            self.app.log.debug("Preparing query '{}'".format(sql_query_parametrized))

            query_keys = [
                t[1]
                for t in Formatter().parse(sql_query_parametrized)
                if t[1] is not None
            ]
            self.app.log.debug("Tokens used by query: '{}'".format(query_keys))

            # convert CLI list of query params to a dict
            quey_params_dict: Dict = {
                query_param.split("=")[0]: query_param.split("=")[1]
                for query_param in query_params_list
            }
            self.app.log.debug("Token values from CLI: '{}'".format(quey_params_dict))

            sql_query: str = sql_query_parametrized.format(**quey_params_dict)

            sql_result: Optional[Cursor] = None
            var_mapping: Dict = param["var_mapping"]

            sql_result = self._query_db(sql_query)
            if sql_result:
                data_tuples: List = sql_result.fetchall()
                data_header: List = [h[0] for h in sql_result.description]
                data_dicts: List[Dict] = [
                    {key: value for key, value in zip(data_header, row)}
                    for row in data_tuples
                ]

                self.app.log.debug("Resulting data '{}'".format(data_dicts))

                for var_key, var_value in var_mapping.items():
                    if var_value == "*":
                        template_input_data.update({var_key: data_dicts})
                    else:
                        template_input_data.update(
                            {var_key: data_dicts[0].get(var_value, "None")}
                        )

        jinja_env: Environment = Environment(  # noqa: S701
            loader=FileSystemLoader(
                self.app.config.get("yager", "data")["template_dir"]
            ),
            autoescape=False,
        )
        template = jinja_env.get_template(report_config["template_file"])
        output_from_parsed_template = template.render(template_input_data)
        print(output_from_parsed_template)

        self.app.log.info("Finished report template '{}'".format(report_config["name"]))

    @ex(
        help="generate database from configured data sources",
        arguments=[
            (
                ["--file", "-f"],
                {
                    "help": "path to XML file with data \
                        (could be repetated)",
                    "action": "append",
                    "metavar": "PATH",
                    "dest": "xml_list",
                },
            ),
        ],
    )
    def refresh_db(self) -> None:
        """Generate database from configured layout and data sources."""
        # Stop processing, if DB is not available
        if self.app.db_cursor is None:
            self.app.log.error("No database connection")
            return

        # get required params from app config
        all_data_configs: List[Dict] = self.app.config.get("yager", "data")

        # get required params from CLI
        xml_files: str = self.app.pargs.xml_list

        # init local vars
        database_query: Optional[Cursor] = None

        # make backup of main DB
        database_query = self._query_db("PRAGMA database_list;")
        if database_query:
            db_list: List = database_query.fetchall()
            db_name_dict: Dict = dict(map(lambda x: (x[1], x[2]), db_list))
            main_db_path: str = Path(db_name_dict["main"])
            db_backup_name: str = "{}.{}.bak".format(
                main_db_path.name, int(datetime.utcnow().timestamp())
            )

            self.app.log.info(
                "Backup DB '{}' as '{}'".format(main_db_path, db_backup_name)
            )

            copyfile(
                main_db_path, main_db_path.with_name(db_backup_name),
            )

        # delete all tables  from existing DB but leave excluded ones
        database_query = self._query_db(
            "SELECT name FROM sqlite_master WHERE type == 'table';"
        )
        if database_query:
            table_list: List[str] = database_query.fetchall()

            for record_tuple in table_list:
                table = record_tuple[0]
                if table not in all_data_configs["exclude_from_refresh"]:
                    self.app.log.info("Deleting table '{}'".format(table))
                    self._query_db("DROP TABLE {};".format(table))
                else:
                    self.app.log.info("Leaving table '{}' untouched".format(table))

        # create table layout
        for table in all_data_configs["layout"]:
            table_name: str = table["name"]
            table_columns: str = table["columns"].replace("\n", "")
            data_source_type: str = table["data_source"].split(":")[0]
            data_source: str = table["data_source"].split(":")[1]

            self.app.log.info("Creating table '{}'".format(table_name))
            database_query = self._query_db(
                "CREATE TABLE IF NOT EXISTS {} ({})".format(table_name, table_columns)
            )

            self.app.log.debug(
                "Using data source '{}:{}'".format(data_source_type, data_source)
            )
            if data_source_type == "csv":
                data_source_path: Path = Path(data_source)
                row_count: int = 0

                self.app.log.info(
                    "Inserting data from CSV file '{}'".format(data_source_path)
                )

                # read data from CSV
                with open(data_source_path, "r") as csv_file:
                    csv_data = DictReader(csv_file)

                    self._query_db("BEGIN TRANSACTION")

                    for row in csv_data:
                        self._query_db(
                            "INSERT OR IGNORE INTO {} ({}) VALUES ('{}')".format(
                                table_name,
                                ",".join(row.keys()),
                                "','".join(row.values()),
                            )
                        )

                        row_count += 1

                        # Commit to DB every 100 records
                        if row_count % 100 == 0:
                            self._query_db("COMMIT")

                            self.app.log.info(
                                "Inserted {} records...".format(row_count)
                            )

                            self._query_db("BEGIN TRANSACTION")

                    self._query_db("COMMIT")

                self.app.log.info("Total records inserted: {}".format(row_count))

            elif data_source_type == "xml":
                if xml_files:
                    for file_path in xml_files:
                        element_count: int = 0

                        self.app.log.info(
                            "Inserting data from XML file '{}'".format(file_path)
                        )

                        xml_root: Element = xml_parse(file_path).getroot()  # noqa: S314

                        self.app.log.info(
                            "Finding all elements matching XPath '{}'".format(
                                data_source
                            )
                        )

                        xml_data: List[Element] = xml_root.findall(data_source)
                        self.app.log.info("Found {} elements".format(len(xml_data)))

                        self._query_db("BEGIN TRANSACTION")

                        for element in xml_data:
                            input_map: Dict[str] = table["input_map"]
                            input_map_parametrized: Dict[str] = table.get(
                                "input_map_parametrized", {}
                            )
                            row: Dict[str] = {}

                            # Expand straightforward input paramenters into values
                            for input_key, input_value_map in input_map.items():
                                element_mapped: Optional[Element] = element.find(
                                    input_value_map
                                )

                                if element_mapped is not None:
                                    input_value: str = element_mapped.text
                                else:
                                    input_value = "undefined"

                                row.update({input_key: input_value})

                            # Expand parametrized input paramenters into values
                            for (
                                input_key,
                                input_value_map,
                            ) in input_map_parametrized.items():
                                input_value_map_expanded = input_value_map.format(**row)

                                element_mapped: Optional[Element] = xml_root.find(
                                    input_value_map_expanded
                                )

                                if element_mapped is not None:
                                    input_value: str = element_mapped.text
                                else:
                                    input_value = "undefined"

                                row.update({input_key: input_value})

                            self._query_db(
                                "INSERT OR IGNORE INTO {} ({}) VALUES ('{}')".format(
                                    table_name,
                                    ",".join(row.keys()),
                                    "','".join(row.values()),
                                )
                            )

                            element_count += 1

                            # Commit to DB every 100 records
                            if element_count % 100 == 0:
                                self._query_db("COMMIT")

                                self.app.log.info(
                                    "Inserted {} records...".format(element_count)
                                )

                                self._query_db("BEGIN TRANSACTION")

                        self._query_db("COMMIT")

                        self.app.log.info(
                            "Total records inserted: {}".format(element_count)
                        )

                else:
                    self.app.log.error("No XML files specified for data input")

            else:
                self.app.log.error(
                    "Unknown data source type '{}'".format(data_source_type)
                )
