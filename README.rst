Enterprise Search | Workplace Search | <Connector name>
===================================================

<Add short description on the source product>
The <Connector name> provided with Workplace Search automatically synchronizes and enables searching over following items:

* <List of document type supported by the connector>

This connector supports <Supported versions of the source product>

Note: The <Connector name> is a **beta** feature. Beta features are subject to change and are not covered by the support SLA of general release (GA) features. Elastic plans to promote this feature to GA in a future release. 

Requirements
------------

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* Java 7 or higher
* Windows, MacOS or Linux Server (Latest tests occurred on CentOS 7, MacOS (Monterey v12.0.1), &  Windows 10) 

Installation
------------

This connector is a python package that can be installed as a package locally::

    make install_package

This will install all pre-requisites for the package and the package itself for the current user.
In case you use a specific command to run python files, such as 'py', you can add `PYTHON=py` in the above command ::

    make PYTHON_CMD=py install_package 

Note: If you are running the connector on a Windows environment, you need to install 'make' from the command Prompt via ::

    winget install make

Further, provide the path of executable in the environment variables, if not avaialable. By default, the pacakage is installed in following paths:

MacOS: '/Users/<user_name>/Library/Python/3.8/bin'
Linux: './local/bin'
Windows: '\Users\<user_name>\AppData\Roaming\Python\Python38\Scripts'

Considering you are using python 3.8

By default, it uses the command 'python3'
After the package is installed, you can open a new shell and run the connector itself::

    ees_connector <cmd>

<cmd> is the connector command, such as:

- 'bootstrap' to create a content source in Enterprise Search
- 'full-sync' to synchronize all data from <source> to Enterprise Search
- 'incremental-sync' to synchronize recent data from <source> to Enterprise Search
- 'deletion-sync' to remove from Enterprise Search the data recently deleted from <source>
- 'permission-sync' to synchronize permissions of the users from <source> Enterprise Search

The connector will install the supplied config.yml file into the package data files and use it when run without the -c option.
You can either edit supplied config.yml file **before** installing the package, or run the connector with '-c <FILE_NAME>' pointing
to the config file you're willing to use, for example::

    ees_connector -c ~/server-1-config.yml full-sync

Note: -c option is optional only for Linux environments. For Windows and MacOS the user needs to provide the config file via -c option.

In Linux, By default the connector will put its default config file into a `config` directory along the executable. To find the config file
you can run 'which ees_connector' to see where the executable of the connector is, then run 'cd ../config' and you'll find yourself
in the directory with a default 'config.yml' file.

Bootstrapping
-------------

Before indexing can begin, you need a new content source to index against. You
can either get it by creating a new `custom API source <https://www.elastic.co/guide/en/workplace-search/current/workplace-search-custom-api-sources.html>`_
from the Workplace Search admin dashboard or you can just bootstrap it using the
'bootstrap.py' file. To use 'bootstrap.py', make sure you have specified
'enterprise_search.host_url' and 'workplace_search.api_key' in the
'config.yml' file. Follow the instructions in the Workplace Search guide to `create a Workplace Search API key <https://www.elastic.co/guide/en/workplace-search/current/workplace-search-api-authentication.html#auth-token>`_. 

Run the bootstrap command ::

    ees_connector bootstrap --name <Name of the Content Source> --user <Admin Username>

Here, the parameter 'name' is _required_ while 'user' is _optional_.
You will be prompted to share the user's password if 'user' parameter was specified above. If the parameter 'user' was not specified, the connector would use 'workplace_search.api_key' specified in the configuration file for bootstrapping the content source.

Once the content source is created, the content source ID will be printed on the terminal. You can now move on to modifying the configuration file.

Configuration file
------------------

Required fields in the configuration file:

* workplace_search.api_key
* workplace_search.source_id
* enterprise_search.host_url


The field ``object`` Specifies what fields are indexed/excluded in workplace search.
By default all the fields are added if both the ``exclude_fields`` and ``include_fields`` parameter is not specified. 
Example:

objects:
   object_name1:
        include_fields:
             -id
             -title
        exclude_fields:
             -author
    object_name2:
        include_fields:
             -GUID


Running the Connector
---------------------

Running a specific functionality as a recurring process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to run the connectors as a cron job. A sample crontab file is provided in the 'cron/connector.example' file.
You can edit and then add it manually to your crontab with 'crontab -e' or if your system supports cron.d copy or symlink it into '/etc/cron.d/' directory.

The connector will emit logs into stdout and stderr, if logs are needed consider simply piping the output of connectors into
desired file, for example the crontab if you've put config file into '~/.config/config.yml' and
want to have logs in '~/' can look like::

    0 */2 * * * ees_connector incremental-sync >> ~/incremental-sync.log 2>&1
    0 0 */2 * * ees_connector full-sync >> ~/full-sync.log 2>&1
    0 * * * * ees_connector deletion-sync >> ~/deletion-sync.log 2>&1
    */5 * * * * ees_connector permission-sync >> ~/permission-sync.log 2>&1

Indexing
========

You are all set to begin synchronizing documents to Workplace Search. Run the 'incremental-sync' command to start the synchronization. Each consecutive run of 'incremental-sync' will restart from the same place where the previous run ended.
If the permission fetching is enabled in the configuration file, incremental sync also handles document level permission fetching from the <source> and ingests the documents with document level permissions. This will replicate document permissions from <source> to Workplace Search.

Full sync ensures indexing occurs from the 'start_time' provided in the configuration file till the current time of execution. To run full sync, execute the 'full-sync' command.

The connector inherently uses the `Tika module <https://pypi.org/project/tika/>`_ for parsing file contents from attachments. `Tika-python <https://github.com/chrismattmann/tika-python>`_ uses Apache Tika REST server. To use this library, you need to have Java 7+ installed on your system as tika-python starts up the Tika REST server in the background.
Tika Server also detects contents from images by automatically calling Tesseract OCR. To allow Tika to also extract content from images, you need to make sure tesseract is on your path and then restart tika-server in the backgroud(if it is already running), by doing ``ps aux | grep tika | grep server`` and then ``kill -9 <pid>``

Note: To allow Tika to extract content from images, you need to manually install Tesseract OCR.

Sync user permissions
=====================

Run the `permission-sync` command to sync any updates to users and groups in <source> with Workplace Search
To sync permissions, you need to provide a path of csv file in the config field: ``connector.user_mapping``. The first column of each row in this csv is the <source> username 
while the second column is the Workplace Search username.

Removing files deleted in <source> from Enterprise Search
==================================================================

When items are deleted from the <source>, a separate process is required to update Workplace Search accordingly. Run the 'deletion-sync' command for deleting the records from Workplace Search.

Testing connectivity
====================

You can check the connectivity between the <source> and Workplace Search server. 

Use the following command ::bash

    make test_connectivity

This command will attempt to to:
* check connectivity with Workplace Search
* check connectivity with the <source>
* test the basic ingestion and deletion to the Workplace Search

Common Issues
=============

1. At times, the TIKA server fails to start hence content extraction from attachments may fail. To avoid this, make sure Tika is running in the background.

Where can I go to get help?
===========================

The Enterprise Search team at Elastic maintains this library and are happy to help. Try posting your question to the Elastic Enterprise Search `discuss forums <https://discuss.elastic.co/c/enterprise-search/84>`_. 

If you are an Elastic customer, please contact Elastic Support for assistance.
