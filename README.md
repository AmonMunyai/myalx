# myALX

`myalx` is a command-line interface (CLI) tool designed to assist with various tasks related to ALX projects. This CLI offers functionalities to generate files, run self-contained checkers, and create new projects based on ALX intranet data.

## Installation

To install `myalx` CLI, you can follow these steps:

1. First, make sure you have [Python](https://www.python.org/downloads/) and [Poetry](https://python-poetry.org/docs/#installation) installed on your system.

2. Clone this repository:

    ```bash
    git clone https://github.com/AmonMunyai/myalx.git
    ```

3. Navigate to the project directory:

    ```bash
    cd myalx
    ```

4. Install the project dependencies using Poetry:

    ```bash
    poetry install
    ```

5. Optionally, you can create a virtual environment for the project using Poetry:

    ```bash
    poetry shell
    ```

This will activate the virtual environment. You can deactivate it by simply typing `exit`.

Now, `myalx` CLI should be installed and ready to use on your system.

## Usage

Once installed, you can use the `myalx` CLI to perform various tasks. Here are the available commands:

- `genfile <name>`: Generate a new file using predefined templates.

- `runchecker <task>`: Run a self-contained checker.

- `settings`: Get settings values.

- `startproject <url> [<dir>]`: Create a new project. You need to provide a valid ALX project URL. Optionally, you can specify a directory to save the project files. You can provide a project ID, and the CLI will automatically generate the project URL based on the ALX intranet domain.

- `version [--verbose]`: Print myALX version. Use the `--verbose` flag to display additional information.

## Configuration

Before using the CLI, make sure to configure your ALX credentials. You can do this by creating a `.alxconfig` file in your home directory (`~/.alxconfig`) and adding the following environment variables:

```toml
[settings]
EMAIL=your_email@example.com
PASSWORD=your_password

```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`myalx` was created by Amon Munyai. It is licensed under the terms of the MIT license - see the [LICENSE](LICENSE) file for details.

## Credits

`myalx` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).
