import pytest

from myalx.config import AlxConfig


@pytest.fixture
def alx_config(tmp_path):
    """A pytest fixture to create an instance of AlxConfig for testing."""
    config_path = tmp_path / "test_alxconfig.ini"
    config = AlxConfig(config_path)

    try:
        yield config

    finally:
        config.config_path.unlink(missing_ok=True)


def test_set_and_get(alx_config):
    """Test the set and get methods pf AlxConfig for setting and retrieving values."""
    alx_config.set("new_section", "new_key", "new_value")

    assert alx_config.get("new_section", "new_key") == "new_value"


def test_non_existent_key(alx_config):
    """Test the get method of AlxConfig for a non-existent key."""
    assert alx_config.get("non_existent_section", "non_existent_key") is None


def test_update_existing_value(alx_config):
    """Test updating an existing value in the configuration."""
    alx_config.set("new_section", "new_key", "new_value")
    alx_config.set("new_section", "new_key", "updated_value")

    assert alx_config.get("new_section", "new_key") == "updated_value"


def test_remove_value(alx_config):
    """Test removing a value from the configuration."""
    alx_config.set("new_section", "new_key", "new_value")
    alx_config.set("new_section", "new_key", "")

    assert alx_config.get("new_section", "new_key") is None


def test_custom_default_path(tmp_path):
    """Test specifying custom default paths for configuration and key files."""
    custom_config_path = tmp_path / "custom_config.ini"
    config = AlxConfig(custom_config_path)

    assert config.config_path == custom_config_path


def test_create_section(alx_config):
    """Test creating a new section in the configuration."""
    alx_config.set("new_section", "new_key", "new_value")

    assert alx_config.get("new_section", "new_key") == "new_value"


def test_save_configuration(alx_config, tmp_path):
    """test saving the configuration file."""
    alx_config.set("new_section", "new_key", "new_value")
    alx_config.save()

    new_config = AlxConfig(tmp_path / "test_alxconfig.ini")
    assert new_config.get("new_section", "new_key") == "new_value"


def test_invalid_configuration_file(tmp_path):
    """Test handling an invalid configuration file."""
    invalid_config_path = tmp_path / "invalid_config.ini"
    invalid_config_path.write_text("invalid content")

    with pytest.raises(Exception):
        AlxConfig(invalid_config_path)


def test_default_values(alx_config):
    """Test retrieving default values for non-existent options."""
    assert (
        alx_config.get(
            "non_existent_section", "non_existent_key", default="default_value"
        )
        == "default_value"
    )
