# A playground for using Azure OIDC with Confluent Cloud with Python >=3.8

## Precondition

Please set up Azure and Confluent Cloud as described in the main README.md file. Alternatively, provide API keys for Confluent Cloud.

This code uses `uv` for package management.

## Development

### Install all packages with uv

For development including tools for generating documentation, use:

```console
uv sync
```

This will create a virtual environment in `.venv`.

### Configuration file

In the python folder, copy the file `example-config.yaml` to `config.yaml` and set the appropriate values.

### Authenticate to Azure

Before running the code, you need to authenticate to Azure. There are multiple ways to do that. If you use VS Code, you can install the extension `Azure Account` and authenticate directly in VS Code using the command by calling `Azure: Sign in to Azure Cloud`. Alternatively, install the `az` command line tool and run `az login`.

### Runing the code

In general, the code can be run with poetry like this:

```console
uv run python <src-file> [<arg>]
```

### Examples

List all organizations by running

```console
uv run python src/confluent_cloud_api_examples/ccloud_list_environments.py  config.yaml
```

## License

Copyright Eike Thaden, 2026.

See LICENSE file
