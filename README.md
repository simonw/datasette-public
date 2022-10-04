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

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-public
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
