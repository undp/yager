# Yager = Yet Another GEneric Reporter

[![Python 3.7+](https://img.shields.io/badge/Python-3.7+-blue.svg)][PythonRef] [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)][BlackRef] [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)][MITRef]

[PythonRef]: https://docs.python.org/3.7/
[BlackRef]: https://github.com/ambv/black
[MITRef]: https://opensource.org/licenses/MIT

`yager` is Yet Another GEneric Reporter tool for parsing of XML data into an SQLite database and subsequent universal reporting based on SQL queries and Jinja2 templates.

## Getting Started

### Installing

`yager` is distributed through the [Python Package Index][PyPIRef] as [yager][PyPIProjRef]. Run the following command to:

[PyPIRef]: https://pypi.org
[PyPIProjRef]:https://pypi.org/project/yager/

* install a specific version

    ```sh
    pip install "yager==0.1"
    ```

* install the latest version

    ```sh
    pip install "yager"
    ```

* upgrade to the latest version

    ```sh
    pip install --upgrade "yager"
    ```

* install optional DEV dependencies like `pytest` framework and plugins necessary for performance and functional testing

    ```sh
    pip install "yager[test]"
    ```

### Configuring

`yager` looks for a `YAML` configuration file in the following locations:

* `/etc/yager/yager.yaml`
* `~/.config/yager/yager.yaml`
* `~/.yager/config/yager.yaml`
* `~/.yager.yaml`

Below is the [example configuration file][yagerConfigRef] that parses XML data from [Qualys Cloud Agent API][QualysCloudAgentAPIRef] about Azure VMs and generates reports for each Azure Subscription.

[yagerConfigRef]: config/etc/yager_example.yaml
[QualysCloudAgentAPIRef]: https://www.qualys.com/docs/qualys-ca-api-user-guide.pdf

## Usage

### Generic

```term
usage: yager [-h] [-d] [-q] [-v] {query,refresh-db,report} ...

Yet Another GEneric Reporter tool for parsing of XML data into an SQLite database and subsequent universal reporting based on SQL queries and Jinja2 templates.

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           full application debug mode
  -q, --quiet           suppress all console output
  -v, --version         show program's version number and exit

sub-commands:
  {query,refresh-db,report}
    query               execute a query against database
    refresh-db          generate database from configured data sources
    report              execute a pre-configured report

Usage: yager {sub-command} {options}
```

### Query

```term
usage: yager query [-h] [--output FORMAT] QUERY

positional arguments:
  QUERY                 query to be executed

optional arguments:
  -h, --help            show this help message and exit
  --output FORMAT, -o FORMAT
                        defines how to format the output (choose from 'csv' or
                        'table'; default: 'table')
```

### Refresh-db

```term
usage: yager refresh-db [-h] [--file PATH]

optional arguments:
  -h, --help            show this help message and exit
  --file PATH, -f PATH  path to XML file with data (could be repetated)
```

### Report

```term
usage: yager report [-h] [--param PARAM] NAME

positional arguments:
  NAME                  report to be executed

optional arguments:
  -h, --help            show this help message and exit
  --param PARAM, -p PARAM
                        NAME=VALUE pair defining a global query parameter to
                        be used for each query in the template (could be
                        repetated)
```

### Examples

Refresh the database using the layout and data sources described in the YAML config.

```sh
$ yager refresh-db -f data.xml
```

Generate report based on SQL queries and Jinja2 templates defined in the YAML config.

```sh
$ yager report TEMPLATE --param KEY1=VALUE1 --param KEY2=VALUE2
```

## Requirements

* Python >= 3.7

## Built using

* [Cement Framework][CementRef] - CLI application framework

[CementRef]: https://builtoncement.com/

## Versioning

We use [Semantic Versioning Specification][SemVer] as a version numbering convention.

[SemVer]: http://semver.org/

## Release History

For the available versions, see the [tags on this repository][RepoTags]. Specific changes for each version are documented in [CHANGELOG.md][ChangelogRef].

Also, conventions for `git commit` messages are documented in [CONTRIBUTING.md][ContribRef].

[RepoTags]: https://github.com/undp/yager/tags
[ChangelogRef]: CHANGELOG.md
[ContribRef]: CONTRIBUTING.md

## Authors

* **Oleksiy Kuzmenko** - [OK-UNDP@GitHub][OK-UNDP@GitHub] - *Initial design and implementation*

[OK-UNDP@GitHub]: https://github.com/OK-UNDP

## Acknowledgments

* Hat tip to all individuals shaping design of this project by sharing their knowledge in articles, blogs and forums.

## License

Unless otherwise stated, all authors (see commit logs) release their work under the [MIT License][MITRef]. See [LICENSE.md][LicenseRef] for details.

[LicenseRef]: LICENSE.md

## Contributing

There are plenty of ways you could contribute to this project. Feel free to:

* submit bug reports and feature requests
* outline, fix and expand documentation
* peer-review bug reports and pull requests
* implement new features or fix bugs

See [CONTRIBUTING.md][ContribRef] for details on code formatting, linting and testing frameworks used by this project.
