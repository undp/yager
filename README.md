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

```yaml
### Yager Configuration Settings
---
yager:
  # Toggle application level debug (does not toggle Cement framework debugging)
  # debug: true

  # Data location and layout
  data:
    # URI to the SQLite3 database with Qualys data
    db_uri: "file:./instance/data/results.db"

    # Tables exclude from deletion during `refresh-db`
    exclude_from_refresh: [
      "QualysKB",
    ]

    # List of table definitions
    layout:
        # Table name
      - name: AzureSubscriptions
        # Table columns described as an SQL statement;
        # Used in `CREATE TABLE IF NOT EXISTS {name} ({columns})`
        columns: |
          id TEXT PRIMARY KEY,
          name TEXT,
          contactName TEXT,
          contactEmail TEXT
        # Source of data for the table in a form of `{type}:{locator}`
        #   {type} could be `csv` or `xml`
        #   {locator} is a file path for `csv` type or XPath for `xml`
        #   XML files are provided with `--file path/to/file.xml` option
        data_source: csv:./instance/subscriptions.csv

      - name: HostAssets
        columns: |
          id INTEGER PRIMARY KEY,
          name TEXT,
          fqdn TEXT,
          os TEXT,
          firstSeen DATETIME,
          lastUpdated DATETIME,
          lastVulnScan DATETIME,
          azureVmId TEXT,
          azureRgName TEXT,
          azurePublicIp TEXT,
          azurePrivateIp TEXT,
          azureSubscriptionId TEXT,
          FOREIGN KEY (azureSubscriptionId)
              REFERENCES AzureSubscriptions (id)
        data_source: xml:.//HostAsset
        # Mapping between table columns and XPath to text values
        # of sub-elements for each element returned by `data_source` XPath
        input_map:
          id: id
          name: name
          fqdn: fqdn
          os: os
          firstSeen: created
          lastUpdated: modified
          lastVulnScan: lastVulnScan
          azureVmId: ./sourceInfo/list/AzureAssetSourceSimple/vmId
          azureRgName: ./sourceInfo/list/AzureAssetSourceSimple/resourceGroupName
          azurePublicIp: ./sourceInfo/list/AzureAssetSourceSimple/publicIpAddress
          azurePrivateIp: ./sourceInfo/list/AzureAssetSourceSimple/privateIpAddress
          azureSubscriptionId: ./sourceInfo/list/AzureAssetSourceSimple/subscriptionId

      - name: Vulns
        columns: |
          id INTEGER PRIMARY KEY,
          qid INTEGER,
          firstFound DATETIME,
          lastFound DATETIME,
          hostAssetsId INTEGER,
          FOREIGN KEY (hostAssetsId)
              REFERENCES HostAssets (id)
        data_source: xml:.//HostAssetVuln
        input_map:
          id: hostInstanceVulnId
          qid: qid
          firstFound: firstFound
          lastFound: lastFound
        # Similar to `input_map` but mapping is parametrized with any {table_column}
        # already defined in the `input_map` section. Prior to running XPath match,
        # each {table_column} is expanded with a value already acquired for `input_map`.
        input_map_parametrized:
          hostAssetsId: ".//HostAssetVuln/[hostInstanceVulnId='{id}']/.../.../.../id"

    # Path to directory with Jinja2 templates for reports
    template_dir: "./config/templates/"

  # Templated reports
  reports:
    - name: "single_sub_md"
      description: |
        Report provides detailed Qualys vulnerability data for an individual Azure subscription.
        It expects the following parameters to be provided in CLI:
          * `sub_id` - Subscription ID from `AzureSubscriptions` table
      template_file: "report_single_sub_md.j2"
      template_params:
        - query: |
            -- Subscription details
            SELECT
              id,
              name,
              contactName,
              contactEmail
            FROM
              AzureSubscriptions
            WHERE
              id == '{sub_id}'
          var_mapping:
            subscription_id: id
            subscription_name: name
            subscription_poc_name: contactName
            subscription_poc_email: contactEmail

        - query: |
            -- Vuln details for all hosts in subscription
            SELECT
                HostAssets.name as host_name,
                HostAssets.azureVmId as host_vm_id,
                Vulns.firstFound as vuln_seen_first,
                Vulns.lastFound as vuln_seen_last,
                Vulns.qid as vuln_qid,
                QualysKB.severity_level as vuln_level
            FROM
                HostAssets
                INNER JOIN Vulns ON Vulns.hostAssetsId = HostAssets.id
                INNER JOIN QualysKB ON QualysKB.qid = Vulns.qid
            WHERE
                HostAssets.azureSubscriptionId == '{sub_id}'
                AND QualysKB.vuln_type != "Information Gathered";
          var_mapping:
            all_vuln_details: "*"

        - query: |
            -- Additional host details
            SELECT
                HostAssets.name as host_name,
                HostAssets.fqdn as host_fqdn,
                HostAssets.os as host_os,
                HostAssets.lastVulnScan as host_last_scan,
                HostAssets.azureRgName as host_rg,
                HostAssets.azureVmId as host_vm_id,
                HostAssets.azurePrivateIp as host_priv_ip,
                HostAssets.azurePublicIp as host_pub_ip
            FROM
                HostAssets
            WHERE
                HostAssets.azureSubscriptionId == '{sub_id}'
          var_mapping:
            all_host_details: "*"

        - query: |
            -- Reference information from Qualys Knowledge Base
            SELECT
                QualysKB.qid as vuln_qid,
                QualysKB.severity_level as vuln_level,
                QualysKB.title as vuln_title,
                QualysKB.diagnosis as vuln_details,
                QualysKB.consequence as vuln_risk,
                QualysKB.solution as vuln_solution
            FROM
                QualysKB
          var_mapping:
            kb_details: "*"

# Logging configuration
log.colorlog:
  # Whether or not to colorize the log file.
  # colorize_file_log: false

  # Whether or not to colorize the console log.
  # colorize_console_log: true

  # Where the log file lives (no log file by default)
  # file: null

  # The level for which to log.  One of: info, warning, error, fatal, debug
  # level: INFO

  # Whether or not to log to console
  # to_console: true

  # Whether or not to rotate the log file when it reaches `max_bytes`
  # rotate: false

  # Max size in bytes that a log file can grow until it is rotated.
  # max_bytes: 512000

  # The maximum number of log files to maintain when rotating
  # max_files: 4

```

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
