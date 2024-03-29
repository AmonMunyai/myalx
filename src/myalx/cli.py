import sys

import click

from .config import AlxConfig
from .spider import run_spider
from .utils import AlxProject


@click.group()
def main():
    """Main entry point for myALX."""
    pass


@main.command()
@click.argument("section_key", type=str)
@click.argument("value", type=str, required=False)
def config(section_key, value):
    """Configure settings for myALX."""
    try:
        section, key = section_key.split(".")

    except ValueError:
        msg = "key does not contain a section: {}".format(section_key)
        raise click.ClickException(msg)

    if not key:
        msg = "key does not contain a variable name: {}".format(section_key)
        raise click.ClickException(msg)

    alx_config = AlxConfig()

    try:
        if value is not None:
            alx_config.set(section, key, value)

        else:
            value = alx_config.get(section, key)

            if value is None:
                sys.exit(1)

            click.echo(value)

    except Exception as e:
        raise e


@main.command()
@click.argument("project_url", type=str)
def startproject(project_url):
    """Create a new project."""
    try:
        # TODO: make email and password retrieval more secure
        email = input("Email: ")
        password = input("Password: ")

        scraped_data = run_spider(project_url, email, password)

        project = AlxProject(scraped_data)
        project.start()

    except Exception as e:
        raise e


if __name__ == "__main__":
    main()