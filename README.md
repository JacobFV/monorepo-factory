# Monorepo Factory

Monorepo Factory is a command-line tool designed to streamline the process of setting up repositories and submodules based on a TOML configuration file. It automates the creation of monorepos, allowing you to define complex repository structures in a simple and declarative manner.

## Features

- **Automated Repository Creation**: Generate multiple repositories with predefined settings.
- **Submodule Support**: Easily configure and include submodules within your repositories.
- **Pattern Matching**: Apply patterns to match and configure repositories dynamically.
- **Customizable Initialization**: Initialize repositories with custom READMEs and other initial files.

## Installation

Monorepo Factory can be installed using `pipx`, which allows you to run Python applications in isolated environments. To install `pipx` and Monorepo Factory, follow these steps:

```bash
# Install pipx if it's not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```
```bash
# Install Monorepo Factory using pipx
pipx install monorepo-factory
```
## Usage

To use Monorepo Factory, you need to have a TOML configuration file that defines the structure of your repositories and any patterns or submodules you want to include.

```bash
# Run Monorepo Factory with the path to your TOML configuration file
monorepo_factory PATH_TO_TOML_FILE
```

For detailed usage instructions, you can use the `--help` flag:

```bash
$ poetry run python monorepo_factory --help

 Usage: monorepo_factory [OPTIONS] TOML_FILE

 Main function to set up repositories and submodules from a TOML configuration file.

╭─ Arguments ────────────────────────────────────────────╮
│ *    toml_file      TEXT  [default: None] [required]   │
╰────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────╮
│ --help          Show this message and exit.            │
╰────────────────────────────────────────────────────────╯
```


## Configuration

Your TOML configuration file should define the repositories, submodules, and any patterns that you want to apply. Here's an example structure of what the TOML file might look like:

```toml
# Define repositories and their properties
[[repo]]
name = "main-repo"
description = "This is the main repository."
# Define submodules for a repository
[[repo.subrepos]]
name = "submodule-1"
path = "libs/submodule-1"
# Define patterns to apply settings to repositories matching a pattern
[[pattern]]
pattern = "service-"
description = "Services repository pattern."
```

## Contributing

Contributions to Monorepo Factory are welcome! Please read the `CONTRIBUTING.md` file for guidelines on how to contribute to this project.

## License

Monorepo Factory is released under the MIT License. See the `LICENSE` file for more information.