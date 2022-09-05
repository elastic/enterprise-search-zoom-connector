![logo-enterprise-search](https://user-images.githubusercontent.com/90465691/166445205-f225e376-a6d7-44bc-9998-5c7b1f7e20f2.png)

[Elastic Enterprise Search](https://www.elastic.co/guide/en/enterprise-search/current/index.html) | [Elastic Workplace Search](https://www.elastic.co/guide/en/workplace-search/current/index.html)

# Zoom connector package

Use this _Elastic Enterprise Search Zoom connector package_ to deploy and run a Zoom connector on your own infrastructure. The connector extracts and syncs data from [Zoom](https://support.zoom.us/hc/en-us). The data is indexed into an Enterprise Search content source within an Elastic deployment.

⚠️ _This connector package is a **beta** feature._
Beta features are subject to change and are not covered by the support SLA of generally available (GA) features. Elastic plans to promote this feature to GA in a future release.

ℹ️ _This connector package requires a compatible Elastic subscription level._
Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

**Table of contents:**

- [Setup and basic usage](#setup-and-basic-usage)
  - [Gather Zoom OAuth App details](#gather-zoom-oauth-app-details)
  - [Gather Elastic details](#gather-elastic-details)
  - [Create an Enterprise Search API key](#create-an-enterprise-search-api-key)
  - [Create an Enterprise Search content source](#create-an-enterprise-search-content-source)
  - [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
  - [Install the connector](#install-the-connector)
  - [Configure the connector](#configure-the-connector)
  - [Test the connection](#test-the-connection)
  - [Sync data](#sync-data)
  - [Log errors and exceptions](#log-errors-and-exceptions)
  - [Schedule recurring syncs](#schedule-recurring-syncs)
- [Troubleshooting](#troubleshooting)
  - [Troubleshoot extraction](#troubleshoot-extraction)
  - [Troubleshoot syncing](#troubleshoot-syncing)
- [Advanced usage](#advanced-usage)
  - [Customize extraction and syncing](#customize-extraction-and-syncing)
  - [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)
- [Connector reference](#connector-reference)
  - [Data extraction and syncing](#data-extraction-and-syncing)
  - [Sync operations](#sync-operations)
  - [Command line interface (CLI)](#command-line-interface-cli)
  - [Configuration settings](#configuration-settings)
  - [Zoom OAuth app compatibility](#zoom-oauth-app-compatibility)
  - [Enterprise Search compatibility](#enterprise-search-compatibility)
  - [Runtime dependencies](#runtime-dependencies)
  - [Connector Limitations](#connector-limitations)

## Setup and basic usage

Complete the following steps to deploy and run the connector:

1. [Gather Zoom OAuth App details](#gather-zoom-oauth-app-details)
1. [Gather Elastic details](#gather-elastic-details)
1. [Create an Enterprise Search API key](#create-an-enterprise-search-api-key)
1. [Create an Enterprise Search content source](#create-an-enterprise-search-content-source)
1. [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
1. [Install the connector](#install-the-connector)
1. [Configure the connector](#configure-the-connector)
1. [Test the connection](#test-the-connection)
1. [Sync data](#sync-data)
1. [Log errors and exceptions](#log-errors-and-exceptions)
1. [Schedule recurring syncs](#schedule-recurring-syncs)

The steps above are relevant to all users. Some users may require additional features. These are covered in the following sections:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather Zoom OAuth App details

Before deploying the connector, you'll need to gather relevant details about your Zoom OAuth App. First, the user needs to create a Zoom OAuth Account level app in [Zoom App Marketplace](https://marketplace.zoom.us/).

First, ensure your Zoom OAuth app is [compatible](#zoom-oauth-app-compatibility) with the Zoom connector package.

Then, collect the information that is required to connect to Zoom:

- The [zoom.client_id](#zoomclient_id-required) will be used to log in to the Zoom Oauth app.
- The [zoom.client_secret](#zoomclient_secret-required) will be used to log in to the Zoom Oauth app.
- The [zoom.authorization_code](#zoomauthorization_code-required) will be used to fetch the refresh token and access token to make API requests for fetching the data from Zoom.
- The [zoom.redirect_uri](#zoomredirect_uri-required) URI to handle successful user authorization. It must match with Development or Production Redirect URI in your OAuth app settings.

Later, you will [configure the connector](#configure-the-connector) with these values.

Some connector features require additional details. Review the following documentation if you plan to use these features:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather Elastic details

First, ensure your Elastic deployment is [compatible](#enterprise-search-compatibility) with the Zoom connector package.

Next, determine the [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

Later, you will [configure the connector](#configure-the-connector) with this value.

You also need an Enterprise Search API key and an Enterprise Search content source ID. You will create those in the following sections.

If you plan to use document-level permissions, you will also need user identity information. See [Use document-level permissions (DLP)](#use-document-level-permissions-dlp) for details.

### Create an Enterprise Search API key

Each Zoom connector authorizes its connection to Elastic using an Enterprise Search API key.

Create an API key within Kibana. See [Enterprise Search API keys](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-api-authentication.html#auth-token).

### Create an Enterprise Search content source

Each Zoom connector syncs data from Zoom into an Enterprise Search content source.

Create a content source within Kibana:

1. Navigate to **Enterprise Search** → **Workplace Search** → **Sources** → **Add Source** → **Zoom**.
1. Choose **Configure Zoom**.

Record the ID of the new content source. This value is labeled *Source Identifier* within Kibana. Later, you will [configure the connector](#configure-the-connector) with this value.

**Alternatively**, if you have already deployed a Zoom connector, you can use the connector's `bootstrap` command to create the content source. See [`bootstrap` command](#bootstrap-command).

### Choose connector infrastructure and satisfy dependencies

After you've prepared the two services, you are ready to connect them.

Provision a Windows, MacOS, or Linux server for your Zoom connectors.

The infrastructure must provide the necessary runtime dependencies. See [Runtime dependencies](#runtime-dependencies).

Clone or copy the contents of this repository to your infrastructure.

### Install the connector

After you've provisioned infrastructure and copied the package, use the provided `make` target to install the connector:

```shell
make install_package
```

This command runs as the current user and installs the connector and its dependencies.

Note: By Default, the package installed supports Enterprise Search version 8.0 or above. In order to use the connector for older versions of Enterprise Search(less than version 8.0) use the ES_VERSION_V8 argument while running make install_package or make install_locally command:

```shell
make install_package ES_VERSION_V8=no
```

ℹ️ Within a Windows environment, first install `make`:

```
winget install make
```

Next, ensure the `ees_zoom` executable is on your `PATH`. For example, on macOS:

```shell
export PATH=/Users/shaybanon/Library/Python/3.8/bin:$PATH
```

Note: If you are running the connector on Windows, please ensure Microsoft Visual C++ 14.0 or greater is installed.

The following table provides the installation location for each operating system:

| Operating system | Installation location                                        |
| ---------------- | ------------------------------------------------------------ |
| Linux            | `./local/bin`                                                |
| macOS            | `/Users/<user_name>/Library/Python/3.8/bin`                  |
| Windows          | `\Users\<user_name>\AppData\Roaming\Python\Python38\Scripts` |

### Configure the connector

You must configure the connector to provide the information necessary to communicate with each service. You can provide additional configurations to customize the connector for your needs.

Create a [YAML](https://yaml.org/) configuration file at any pathname. Later, you will include the [`-c` option](#-c-option) when running [commands](#command-line-interface-cli) to specify the pathname to this configuration file.

_Alternatively, in Linux environments only_, locate the default configuration file created during installation. The file is named `zoom_connector.yml` and is located within the `config` subdirectory where the package files were installed. See [Install the connector](#install-the-connector) for a listing of installation locations by the operating system. When you use the default configuration file, you do not need to include the `-c` option when running commands.

After you've located or created the configuration file, populate each of the configuration settings. Refer to the [settings reference](#configuration-settings). You must provide a value for all required settings.

Use the additional settings to customize the connection and manage features such as document-level permissions. See:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Test the connection

After you’ve configured the connector, you can test the connection between Elastic and Zoom. Use the following `make` target to test the connection:

```shell
make test_connectivity
```

### Sync data

After you’ve confirmed the connection between the two services, you are ready to sync data from Zoom to Elastic.

The following table lists the available [sync operations](#sync-operations), as well as the [commands](#command-line-interface-cli) to perform the operations.

| Operation                             | Command                                         |
| ------------------------------------- | ----------------------------------------------- |
| [Incremental sync](#incremental-sync) | [`incremental-sync`](#incremental-sync-command) |
| [Full sync](#full-sync)               | [`full-sync`](#full-sync-command)               |
| [Deletion sync](#deletion-sync)       | [`deletion-sync`](#deletion-sync-command)      |
| [Permission sync](#permission-sync)   | [`permission-sync`](#permission-sync-command)   |

Begin syncing with an *incremental sync*. This operation begins [extracting and syncing content](#data-extraction-and-syncing) from Zoom to Elastic. If desired, [customize extraction and syncing](#customize-extraction-and-syncing) for your use case.

Review the additional sync operations to learn about the different types of syncs. Additional configuration is required to use [document-level permissions](#use-document-level-permissions-dlp).

You can use the command-line interface to run sync operations on-demand, but you will likely want to [schedule recurring syncs](#schedule-recurring-syncs).

### Log errors and exceptions

The various [sync commands](#command-line-interface-cli) write logs to standard output and standard error.

To persist logs, redirect standard output and standard error to a file. For example:

```shell
ees_zoom -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
```

You can use these log files to implement your own monitoring and alerting solution.

Configure the log level using the [`log_level` setting](#log_level).

### Schedule recurring syncs

Use a job scheduler, such as `cron`, to run the various [sync commands](#command-line-interface-cli) as recurring syncs.

The following is an example crontab file in linux:

```crontab
PATH=/home/<user_name>/.local/bin
0 */2 * * * ees_zoom -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
0 0 */2 * * ees_zoom -c ~/config.yml full-sync >>~/full-sync.log 2>&1
0 * * * * ees_zoom -c ~/config.yml deletion-sync >>~/deletion-sync.log 2>&1
*/5 * * * * ees_zoom -c ~/config.yml permission-sync >>~/permission-sync.log 2>&1
```

This example redirects standard output and standard error to files, as explained here: [Log errors and exceptions](#log-errors-and-exceptions).

Use this example to create your own crontab file. Manually add the file to your crontab using `crontab -e`. Or, if your system supports cron.d, copy or symlink the file into `/etc/cron.d/`.


⚠️**Note**: It's possible that scheduled jobs may overlap.
To avoid multiple crons running concurrently, you can use [flock](https://manpages.debian.org/testing/util-linux/flock.1.en.html) with cron to manage locks. The `flock` command is part of the `util-linux` package. You can install it with `yum install util-linux`
or `sudo apt-get install -y util-linux`.
Using flock ensures the next scheduled cron runs only after the current one has completed execution. 

Let's consider an example of running incremental-sync as a cron job with flock:

```crontab
0 */2 * * * /usr/bin/flock -w 0 /var/cron_indexing.lock ees_zoom -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
```

Note: If the flock is added for multiple commands in crontab, make sure you mention different lock names(eg: /var/cron_indexing.lock in the above example) for each job else the execution of one command will prevent other command to execute.

## Troubleshooting

To troubleshoot an issue, first view your [logged errors and exceptions](#log-errors-and-exceptions).

Use the following sections to help troubleshoot further:

- [Troubleshoot extraction](#troubleshoot-extraction)
- [Troubleshoot syncing](#troubleshoot-syncing)

If you need assistance, use the Elastic community forums or Elastic support:

- [Enterprise Search community forums](https://discuss.elastic.co/c/enterprise-search/84)
- [Elastic Support](https://support.elastic.co)

### Troubleshoot extraction

The following sections provide solutions for content extraction issues.

#### Issues extracting content from attachments

The connector uses the [Tika module](https://pypi.org/project/tika/) for parsing file contents from attachments. [Tika-python](https://github.com/chrismattmann/tika-python) uses Apache Tika REST server. To use this library, you need to have Java 7+ installed on your system as tika-python starts up the Tika REST server in the background.

At times, the TIKA server fails to start hence content extraction from attachments may fail. To avoid this, make sure Tika is running in the background.

#### Issues extracting content from images

Tika Server also detects contents from images by automatically calling Tesseract OCR. To allow Tika to also extract content from images, you need to make sure tesseract is on your path and then restart tika-server in the background (if it is already running). For example, on a Unix-like system, try:

```shell
ps aux | grep tika | grep server # find PID
kill -9 <PID>
```

To allow Tika to extract content from images, you need to manually install Tesseract OCR.

### Troubleshoot syncing

The following sections provide solutions for issues related to syncing.

#### **Indexing issues:**

* ***For all [meetings](https://marketplace.zoom.us/docs/api-reference/zoom-api/methods#tag/Meetings):***

  - Users can only index meetings that are unexpired.

  - MeetingId will expire in 30 days.

  - Thus, users can only index meetings that are less than a month old.

* ***For all [chat-messages](https://marketplace.zoom.us/docs/api-reference/chat/methods/#tag/Chat-Messages):***

  - Users can only index chats and files that are less than 6 months old.

* ***For all [recordings](https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/recordingsList):***

  - Users can only index recordings that are less than a month old.

* ***For all [past_meetings](https://marketplace.zoom.us/docs/api-reference/zoom-api/methods#operation/pastMeetings):***

  - Users can only index past meetings instances that are less than a month old because the meeting id will expire after 1 month.

#### **Solution:**

  - As a solution, the user has to run the Zoom Connector full-sync or incremental-sync functionality at least once in a span of a month so that all the data will be indexed properly without any data loss.   

#### **Deletion issues:**

* If the user deletes any 'chats' or 'files' which are older than 6 months, or if the user deletes any `meetings`, `recordings`, or `past_meeting` instances which are older than a month from their Zoom account, the user **will not** be able to delete those data from Enterprise Search. These objects are archived.

#### **Solution:**

  - To avoid this issue, the user should run the Zoom Connector `deletion-sync` functionality at least once every 30 days, so that all the deleted data from the Zoom app will also be deleted from Enterprise Search.

#### **Checkpoint Policy:**

  - The connector saves the `checkpoint` as a current time after each iteration of indexing.
  - In case of any intermediate errors while indexing, the `checkpoint` will still be saved as the current time since the documents missed as a part of the current incremental sync should be indexed in the next full sync.

## Advanced usage

The following sections cover additional features that are not covered by the basic usage described above.

After you've set up your first connection, you may want to further customize that connection or scale it to multiple connections.

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Customize extraction and syncing

By default, each connection syncs all [supported Zoom data](#data-extraction-and-syncing) across all Zoom objects.

You can limit which Zoom objects are synced. [Configure](#configure-the-connector) the setting [`objects`](#objects).

You can also customize which objects are synced, and which fields are included and excluded for each object. [Configure](#configure-the-connector) the setting [`objects`](#objects).

Finally, you can set custom timestamps to control which objects are synced, based on their created or modified timestamps. [Configure](#configure-the-connector) the following settings:

- [`start_time`](#start_time)
- [`end_time`](#end_time)

### Use document-level permissions (DLP)

Complete the following steps to use document-level permissions:

1. Enable document-level permissions
1. Map user identities
1. Sync document-level permissions data

#### Enable document-level permissions

Within your configuration, enable document-level permissions using the following setting: [`enable_document_permission`](#enable_document_permission).

#### Map user identities

Copy to your connector a CSV file that provides the mapping of user identities. The file must follow this format:

- First column: zoom_user_id
- Second column: enterprise_search_user_id

Then, configure the location of the CSV file using the following setting: [`zoom.user_mapping`](#zoomuser_mapping).

#### Sync document-level permissions data

Sync document-level permissions data from Zoom to Elastic.

The following sync operations include permissions data:

- [Permission sync](#permission-sync)
- [Incremental sync](#incremental-sync)

Sync this information continually to ensure correct permissions. See [Schedule recurring syncs](#schedule-recurring-syncs).

## Connector reference

The following reference sections provide technical details:

- [Data extraction and syncing](#data-extraction-and-syncing)
- [Sync operations](#sync-operations)
- [Command line interface (CLI)](#command-line-interface-cli)
- [Configuration settings](#configuration-settings)
- [Zoom OAuth app compatibility](#zoom-oauth-app-compatibility)
- [Enterprise Search compatibility](#enterprise-search-compatibility)
- [Runtime dependencies](#runtime-dependencies)

### Data extraction and syncing

Each Zoom connector extracts and syncs the following data from Zoom:

- Users
- Meetings
- Recordings
- Roles
- Groups
- Past Meetings
- Channels
- Chats
- Files

The connector handles Zoom pages composed of various web parts, extracts content from various document formats, and uses optical character recognition (OCR) to extract content from images.

You can customize extraction and syncing per connector. See [Customize extraction and syncing](#customize-extraction-and-syncing).

### Sync operations

The following sections describe the various operations to [sync data](#sync-data) from Zoom to Elastic.

#### Incremental sync

Syncs to Enterprise Search all [supported Zoom data](#data-extraction-and-syncing) *created or modified* since the previous incremental sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), each incremental sync will also perform a [permission sync](#permission-sync).

Perform this operation with the [`incremental-sync` command](#incremental-sync-command).

#### Full sync

Syncs to Enterprise Search all [supported Zoom data](#data-extraction-and-syncing) *created or modified* since the configured [`start_time`](#start_time). Continues until the current time or the configured [`end_time`](#end_time).


Perform this operation with the [`full-sync` command](#full-sync-command).

#### Deletion sync

Deletes from Enterprise Search all [supported Zoom data](#data-extraction-and-syncing) *deleted* since the previous deletion sync.

Perform this operation with the [`deletion-sync` command](#deletion-sync-command).

#### Permission sync

Syncs to Enterprise Search all Zoom document permissions since the previous permission sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), use this operation to sync all updates to users within Zoom.

Perform this operation with the [`permission-sync` command](#permission-sync-command).

### Command line interface (CLI)

Each Zoom connector has the following command-line interface (CLI):

```shell
ees_zoom [-c <pathname>] <command>
```

#### `-c` option

The pathname of the [configuration file](#configure-the-connector) to use for the given command.

```shell
ees_zoom -c ~/config.yml full-sync
```

#### `bootstrap` command

Creates an Enterprise Search content source with the given name. Outputs its ID.

```shell
ees_zoom bootstrap --name 'Accounting documents' --user 'shay.banon'
```

See also [Create an Enterprise Search content source](#create-an-enterprise-search-content-source).

To use this command, you must [configure](#configure-the-connector) the following settings:

- [`enterprise_search.host_url`](#enterprise_searchhost_url-required)
- [`enterprise_search.api_key`](#enterprise_searchapi_key-required)

And you must provide on the command line any of the following arguments that are required:

- `--name` (required): The name of the Enterprise Search content source to create.
- `--user` (optional): The username of the Elastic user who will own the content source. If provided, the connector will prompt for a password. If omitted, the connector will use the configured API key to create the content source.

#### `incremental-sync` command

Performs an [incremental sync](#incremental-sync) operation.

#### `full-sync` command

Performs a [full sync](#full-sync) operation.

#### `deletion-sync` command

Performs a [deletion sync](#deletion-sync) operation.

#### `permission-sync` command

Performs a [permission sync](#permission-sync) operation.

### Configuration settings

[Configure](#configure-the-connector) any of the following settings for a connector:

#### `zoom.client_id` (required)

The client_id of the Zoom OAuth App.

```yaml
zoom.client_id: 'a122dsad123334'
```

#### `zoom.client_secret` (required)

The client_secret of the Zoom OAuth App.

```yaml
zoom.client_secret: 'a122dsad123334asdaddad'
```

#### `zoom.authorization_code` (required)

The authorization code sent at callback time to fetch the access_token and refresh_token.

```yaml
zoom.authorization_code: 'ABCHm_byl3hOl3SZ-5j5jnC-mXyz'
```
#### `zoom.redirect_uri` (required)

URI to handle successful user authorization. It must match with Development or Production Redirect URI in your OAuth app settings.

```yaml
zoom.redirect_uri: 'https://oauth.example.io/v1/callback'
```

#### `enterprise_search.api_key` (required)

The Enterprise Search API key. See [Create an Enterprise Search API key](#create-an-enterprise-search-api-key).

```yaml
enterprise_search.api_key: 'zvksftxrudcitxa7ris4328b'
```
#### `enterprise_search.source_id` (required)

The ID of the Enterprise Search content source. See [Create an Enterprise Search content source](#create-an-enterprise-search-content-source).

```yaml
enterprise_search.source_id: '62461219647336183fc7652d'
```
#### `enterprise_search.host_url` (required)

The [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

```yaml
enterprise_search.host_url: https://my-deployment.ent.europe-west1.gcp.cloud.es.io
```
Note: While using Elastic Enterprise Search version 8.0.0 and above, port must be specified in [`enterprise_search.host_url`](#enterprise_searchhost_url-required)
#### `objects`

Specifies which Zoom objects to sync to Enterprise Search, and for each object, which fields to include and exclude. When the include/exclude fields are empty, all fields are synced.

```yaml
objects:
  users:
      include_fields:
      exclude_fields:
  recordings:
      include_fields:
      exclude_fields:
  channels:
      include_fields:
      exclude_fields:
  roles:
      include_fields:
      exclude_fields:
  meetings:
      include_fields:
      exclude_fields:
  chats:
      include_fields:
      exclude_fields:
  files:
      include_fields:
      exclude_fields:
  past_meetings:
      include_fields:
      exclude_fields:
  groups:
      include_fields:
      exclude_fields:    
```
#### `start_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from Zoom. Determines the *starting* point for a [full sync](#full-sync).

```yaml
start_time: YYYY-MM-DDTHH:MM:SSZ
```

Note: If no value is passed, the default `start_time` value is set to when the Zoom app was created (in RFC 3339 date-time format).

#### `end_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from Zoom. Determines the *stopping* point for a [full sync](#full-sync).

```yaml
end_time: YYYY-MM-DDTHH:MM:SSZ
```

Note: The default value of end_time would be the current date-time in RFC-3339(%Y-%m-%dT%H:%M:%SZ) format.

#### `log_level`

The level or severity that determines the threshold for [logging](#log-errors-and-exceptions) a message. One of the following values:

- `DEBUG`
- `INFO` (default)
- `WARN`
- `ERROR`

```yaml
log_level: INFO
```
By default, it is set to `INFO`.

#### `retry_count`

The number of retries to perform when there is a server error. The connector applies an exponential backoff algorithm to retries.

```yaml
retry_count: 3
```
By default, it is set to `3`.
#### `zoom_sync_thread_count`

The number of threads the connector will run in parallel when fetching documents from the Zoom app. By default, the connector uses 5 threads.

```yaml
zoom_sync_thread_count: 5
```

#### `enterprise_search_sync_thread_count`

The number of threads the connector will run in parallel when indexing documents into the Enterprise Search instance. By default, the connector uses 5 threads.

```yaml
enterprise_search_sync_thread_count: 5
```

For a Linux distribution with at least 2 GB RAM and 4 vCPUs, you can increase the thread counts if the overall CPU and RAM are underutilized i.e. below 60-70%.

#### `enable_document_permission`

Whether the connector should sync [document-level permissions (DLP)](#use-document-level-permissions-dlp) from Zoom.

```yaml
enable_document_permission: Yes
```
By default, it is set to `Yes` i.e. the connector will try to sync document-level permissions.
#### `zoom.user_mapping`

The pathname of the CSV file containing the user identity mappings for [document-level permissions (DLP)](#use-document-level-permissions-dlp).

```yaml
zoom.user_mapping: 'C:/Users/banon/connector/identity_mappings.csv'
```
### Zoom OAuth app compatibility

- Configure one Zoom OAuth Account Level App on
[Zoom App Marketplace](https://marketplace.zoom.us/). 
- This will generate a [zoom.client_id](#zoomclient_id-required) and [zoom.client_secret](#zoomclient_secret-required).
- Add the following scopes in the account-level app, to enable Zoom object fetching.

***Scopes to be added:***
```shell
user:read:admin
meeting:read:admin
chat_channel:read:admin
role:read:admin
recording:read:admin
group:read:admin
chat_messages:read:admin
report:read:admin
```
- The user needs to add [zoom.redirect_uri](#zoomredirect_uri-required) to Zoom Oauth App.
- After adding all the scopes and [zoom.redirect_uri](#zoomredirect_uri-required), user needs to generate [zoom.authorization_code](#zoomauthorization_code-required) using [zoom.client_id](#zoomclient_id-required) and [redirect_uri](#zoomredirect_uri-required) by making a GET call to [Generate-Authorization-Code](https://zoom.us/oauth/authorize).
- Refer [Official Zoom OAuth2.0 Documentation](https://marketplace.zoom.us/docs/guides/auth/oauth/) for more details.

### Enterprise Search compatibility

The Zoom connector package is compatible with Elastic deployments that meet the following criteria:

- Elastic Enterprise Search version greater than or equal to 7.13.0.
- An Elastic subscription that supports this feature. Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

### Runtime dependencies

Each Zoom connector requires a runtime environment that satisfies the following dependencies:

- Windows, MacOS, or Linux server. The connector has been tested with CentOS 7, MacOS Monterey v12.0.1, and Windows 10.
- Python version 3.6 or later.
- To extract content from images: Java version 7 or later, and [`tesseract` command](https://github.com/tesseract-ocr/tesseract) installed and added to `PATH`
- To schedule recurring syncs: a job scheduler, such as `cron`

### Connector Limitations

The following section details limitations of this connector:

- If a host reuses a meeting ID to hold additional meetings, the data associated with this ID will only refer to the latest instance of the meeting.
