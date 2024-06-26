import re
from pathlib import Path
from urllib.parse import urlparse

import click
from decouple import Config, RepositoryEnv
from scrapy.crawler import CrawlerProcess

import myalx
from myalx.project import ProjectCreator
from myalx.spider import AlxSpider


@click.group()
@click.pass_context
def cli(ctx):
    """Main entry point for myALX."""

    config_file_path = Path("~/.alxconfig").expanduser()
    alx_config = Config(RepositoryEnv(config_file_path))
    ctx.obj = {"alx_config": alx_config}


@cli.command()
@click.argument("name")
def genfile(name):
    """Generate new file using pre-defined templates."""
    pass


@cli.command()
@click.argument("task")
def runchecker(task):
    """Run a self-contained checker."""
    pass


@cli.command()
def settings():
    """Get settings values."""
    pass


@cli.command()
@click.argument("url")
@click.argument("dir", required=False)
@click.pass_context
def startproject(ctx, url, dir):
    """Create a new project."""

    alx_config = ctx.obj.get("alx_config", {})
    user_email = alx_config("EMAIL")
    user_password = alx_config("PASSWORD")

    # Validate URL and extract project ID
    allowed_domain = "intranet.alxswe.com"
    if re.match(r"^\d+$", url):
        url = f"https://{allowed_domain}/projects/{url}"

    parsed_url = urlparse(url)
    if not (
        parsed_url.scheme == "https"
        and parsed_url.netloc == allowed_domain
        and re.match(r"/projects/\d+", parsed_url.path)
    ):
        raise click.ClickException("Invalid URL.")

    # Scrape data from URL
    scraped_data = {}

    def item_scraped(data):
        scraped_data.update(data)

    process = CrawlerProcess(
        {
            "ITEM_PIPELINES": {
                "myalx.spider.AlxPipeline": 100,
            },
            "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
            "LOG_LEVEL": "INFO",
            # "LOG_ENABLED": False,
        }
    )
    process.crawl(
        AlxSpider,
        url=url,
        email=user_email,
        password=user_password,
        callback=item_scraped,
    )
    process.start()

    # Create project based on scraped data
    project = ProjectCreator(scraped_data)
    project.start_project()


@cli.command()
def version():
    """Print myALX version."""

    click.echo(f"myALX {myalx.__version__}")


if __name__ == "__main__":
    cli()
