"""
cli.py — Command-line interface for ScreenVault.

Commands:
    screenvault watch       Start watching for new screenshots
    screenvault search      Search your screenshot vault
    screenvault backfill    Process all existing screenshots in the watch folder
    screenvault status      Show queue and processing stats
"""

import os
import json
import requests
import click
from pathlib import Path
from watcher import WATCH_DIR, BACKEND_URL, is_screenshot, upload

USER_ID = os.getenv("SCREENVAULT_USER_ID", "")
HEADERS = {"X-User-Id": USER_ID}


@click.group()
def cli():
    """ScreenVault — search your screenshots by content."""
    pass


@cli.command()
def watch():
    """Start watching for new screenshots."""
    from watcher import start
    start()


@cli.command()
@click.argument("query")
@click.option("--page", default=1, show_default=True)
@click.option("--open", "open_file", is_flag=True, help="Open the top result")
def search(query: str, page: int, open_file: bool):
    """Search screenshots by content. Example: screenvault search 'invoice march'"""
    _require_user_id()
    try:
        response = requests.get(
            f"{BACKEND_URL}/search",
            params={"q": query, "page": page},
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except requests.ConnectionError:
        click.echo(f"Cannot reach backend at {BACKEND_URL}. Is it running?")
        return

    data = response.json()
    results = data.get("results", [])

    if not results:
        click.echo(f"No results for '{query}'")
        return

    click.echo(f"\nFound {data['total']} result(s) for '{query}'\n")
    click.echo(f"{'#':<4} {'Date':<22} {'Description':<60} {'File'}")
    click.echo("-" * 110)

    for i, r in enumerate(results, 1):
        date = r.get("captured_at", "")[:19]
        desc = r.get("description", "")[:58]
        filepath = r.get("filepath", "")
        click.echo(f"{i:<4} {date:<22} {desc:<60} {filepath}")

    if open_file and results:
        top = results[0].get("filepath", "")
        if top and Path(top).exists():
            os.system(f"open '{top}'")
        else:
            click.echo("File not found locally.")


@cli.command()
@click.option("--dir", "watch_dir", default=WATCH_DIR, show_default=True)
@click.option("--limit", default=0, help="Max screenshots to process (0 = all)")
def backfill(watch_dir: str, limit: int):
    """Process all existing screenshots in the watch folder."""
    _require_user_id()
    files = sorted(
        [f for f in Path(watch_dir).iterdir() if is_screenshot(f.name)],
        key=lambda f: f.stat().st_mtime,
    )

    if limit:
        files = files[:limit]

    total = len(files)
    if total == 0:
        click.echo(f"No screenshots found in {watch_dir}")
        return

    click.echo(f"Found {total} screenshots to process...")
    for i, f in enumerate(files, 1):
        click.echo(f"[{i}/{total}] {f.name}")
        upload(str(f))

    click.echo(f"\nBackfill complete — {total} screenshots queued.")


@cli.command()
def status():
    """Show backend queue and processing stats."""
    _require_user_id()
    try:
        response = requests.get(f"{BACKEND_URL}/stats", headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        click.echo(json.dumps(data, indent=2))
    except requests.ConnectionError:
        click.echo(f"Cannot reach backend at {BACKEND_URL}")


def _require_user_id():
    if not USER_ID:
        click.echo("ERROR: SCREENVAULT_USER_ID is not set.")
        click.echo("Set it with: export SCREENVAULT_USER_ID=<your-user-id>")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
