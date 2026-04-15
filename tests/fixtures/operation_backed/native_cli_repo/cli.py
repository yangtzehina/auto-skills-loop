import click
import json


@click.group()
def cli():
    pass


@cli.command("sync")
@click.option("--target", required=True)
@click.option("--json", "as_json", is_flag=True)
def sync(target: str, as_json: bool) -> None:
    payload = {"operation": "sync", "target": target}
    if as_json:
        click.echo(json.dumps(payload))
    else:
        click.echo(f"sync {target}")


@cli.command("inspect")
@click.option("--resource", required=True)
@click.option("--json", "as_json", is_flag=True)
def inspect(resource: str, as_json: bool) -> None:
    payload = {"operation": "inspect", "resource": resource}
    if as_json:
        click.echo(json.dumps(payload))
    else:
        click.echo(f"inspect {resource}")
