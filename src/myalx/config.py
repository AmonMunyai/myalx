from configparser import ConfigParser
from pathlib import Path


class AlxConfig:
    """A configuration manager that handles reading and writing user configuration data."""

    def __init__(self, config_path: str = "~/.alxconfig") -> None:
        self.config_path = Path(config_path).expanduser()
        self.config = self.load()

    def load(self) -> ConfigParser:
        """Load the configuration data from the configuration file."""
        config = ConfigParser()

        if not self.config_path.exists():
            self.config_path.touch()

        config.read(self.config_path)
        return config

    def save(self) -> None:
        """Save the configuration data to the configuration file."""
        with self.config_path.open("w", encoding="utf-8") as config_file:
            self.config.write(config_file)

    def set(self, section: str, key: str, value: str) -> None:
        """Set a configuration value for a given section and key."""
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config[section][key] = value

        if value == "":
            self.config.remove_option(section, key)

        self.save()

    def get(self, section: str, key: str, default=None):
        """Get a configuration value for a given section and key."""
        return self.config.get(section, key, fallback=default)
