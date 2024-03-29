import click


@click.group()
@click.pass_context
def cli(ctx):
    """Main entry point for myALX."""
    pass


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
    pass


@cli.command()
def version():
    """Print myALX version."""
    pass


if __name__ == "__main__":
    cli()
