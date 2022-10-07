# datasette-public

[![PyPI](https://img.shields.io/pypi/v/datasette-public.svg)](https://pypi.org/project/datasette-public/)
[![Changelog](https://img.shields.io/github/v/release/simonw/datasette-public?include_prereleases&label=changelog)](https://github.com/simonw/datasette-public/releases)
[![Tests](https://github.com/simonw/datasette-public/workflows/Test/badge.svg)](https://github.com/simonw/datasette-public/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/datasette-public/blob/main/LICENSE)

Make specific Datasette tables visible to the public

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-public

## Usage

Any tables listed in the `_public_tables` table will be visible to the public, even if the rest of the Datasette instance does not allow anonymous access.

The root user (and any user with the new `public-tables` permission) will get a new option in the table action menu allowing them to toggle a table between public and private.

Installing this plugin also causes `allow-sql` permission checks to fall back to checking if the user has access to the entire database. This is to avoid users with access to a single public table being able to access data from other tables using the `?_where=` query string parameter.

## Configuration

This plugin creates a new table in one of your databases called `_public_tables`.

This table defaults to being created in the first database passed to Datasette.

To create it in a different named database, use this plugin configuration:

```json
{
  "plugins": {
    "datasette-public": {
      "database": "database_to_create_table_in"
    }
  }
}
```

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-public
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
