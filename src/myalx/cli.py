import sys

import click

from .spider import run_spider
from .utils import AlxProject


@click.group()
def main():
    """Main entry point for myALX."""
    pass


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
