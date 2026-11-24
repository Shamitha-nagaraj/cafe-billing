"""Create a consistent private SQLite backup, including committed WAL data."""
import argparse
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from cafe.config import ROOT, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'exports')
    args = parser.parse_args()
    cfg = settings()
    source = cfg['DATABASE'].resolve()
    if not source.is_file():
        parser.error('No database exists yet. Run the app first in the intended mode.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = args.output_dir / f'{source.stem}-{stamp}.sqlite3'
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
    print(f'Private backup saved: {destination.resolve()}')
    print('Keep an additional private copy outside this machine. Do not upload it to GitHub.')


if __name__ == '__main__':
    main()
