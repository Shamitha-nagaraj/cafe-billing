"""Package reviewed source only. Never recursively include a working directory."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
FILES = [
    'README.md', '.gitignore', '.env.example', '.dockerignore', 'requirements.txt',
    'app.py', 'serve.py', 'Dockerfile', 'package_project.py', 'train_sample.py', 'backup_database.py',
    'cafe/__init__.py', 'cafe/config.py', 'cafe/database.py', 'cafe/billing.py',
    'cafe/analytics.py', 'cafe/forecast.py', 'templates/index.html', 'static/app.js', 'static/styles.css',
    'tests/test_app.py', 'tests/test_forecast.py', 'data/sample_daily_sales.csv',
    'docs/LEARNING.md', 'docs/DEPLOYMENT.md', '.github/workflows/tests.yml',
]


def main():
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit('Missing required source files: ' + ', '.join(missing))
    target = ROOT / 'dist' / 'cafe-ledger-github.zip'
    target.parent.mkdir(exist_ok=True)
    with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, arcname=name)
    with ZipFile(target) as archive:
        assert set(archive.namelist()) == set(FILES)
        assert archive.testzip() is None
    print(f'Created {target} ({len(FILES)} source files).')
    print('Extract this ZIP, then upload its CONTENTS to the GitHub repository root.')
    print('The package excludes credentials, local environments, databases, and exports.')


if __name__ == '__main__':
    main()
