# Upload and host Café Ledger

## First: distinguish the three addresses

- `http://127.0.0.1:8080` runs on your own computer.
- `https://github.com/YOUR-USERNAME/cafe-billing-forecast` contains source code.
- A hosting provider's HTTPS address runs the online staff application.

Uploading to GitHub is sufficient to share your code and README. It does not automatically run Python. GitHub Pages is not a suitable host for this Flask/SQLite backend.

## A. Run locally first

1. Install Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/). On Windows enable the installer option to add Python to PATH.
2. Extract the supplied ZIP. Open the folder containing `app.py` and `requirements.txt`.
3. In File Explorer's address bar type `powershell` and press Enter.
4. Run these commands separately:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py --demo
```

5. Open http://127.0.0.1:8080. The demo banner must be visible.
6. Try billing and Sales & forecast. Stop the server with Ctrl+C.
7. Run `app.py` without `--demo` when you want an empty real-sales register. Do not type real business records into demo mode.

You do not need to activate the virtual environment when using the full executable paths above. This also avoids PowerShell activation-policy problems.

## B. Create the GitHub repository

1. Visit [Create a repository](https://github.com/new) while signed in.
2. Repository name: `cafe-billing-forecast`.
3. Description: `Python café billing, sales analytics, and a basic ML sales forecast`.
4. Choose Private for your own work, or Public if you intend to publish the source. Do not include real sales or credentials in either case.
5. Leave the options to add a README, .gitignore, and license unchecked; supplied files already include README and .gitignore. No open-source license is included; choose one deliberately if you want to grant reuse rights.
6. Click Create repository.
7. Choose **uploading an existing file** on the empty repository page.
8. Extract `cafe-ledger-github.zip` on your computer. Open the extracted folder and select its **contents**, not the containing folder and not the ZIP itself.
9. Drag those files and folders into the upload area. Include dotfiles such as `.gitignore`, `.env.example`, `.dockerignore`, and the `.github` directory. If a file manager hides them, enable hidden files or use GitHub Desktop.
10. Commit with the message `Initial cafe billing and sales forecast`.

The repository's first page must show:

```text
cafe/             data/             docs/
static/           templates/        tests/
.github/          .gitignore         .env.example
.dockerignore     Dockerfile         README.md
app.py            serve.py           requirements.txt
train_sample.py   package_project.py backup_database.py
```

Do not upload `.venv`, `.env`, `instance`, live databases, or private exports. The supplied ZIP is built from an explicit source-file allowlist. For later changes, run `python package_project.py` to rebuild it. The browser-upload steps follow [GitHub's upload documentation](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## C. Choose hosting that preserves bills

This version writes SQLite files. It needs **one running application instance, a writable persistent volume, and HTTPS**. A host with only temporary disk storage loses sales after a restart or redeployment. Verify storage support and current charges in the provider's dashboard before provisioning a service. No hosting subscription is necessary to learn locally.

The app uses a staff username and password. Share credentials only with authorized staff. It is not intended to expose all sales anonymously to anyone with the link. HTTP Basic authentication is a small starter solution; a larger team needs proper user accounts, roles, session management, and audit records.

## D. Hosting settings for this exact project

Use these values on a Python host:

| Setting | Value |
|---|---|
| Source repository | Your `cafe-billing-forecast` repository |
| Branch | `main` |
| Root directory | Blank, if `requirements.txt` is at repository root |
| Runtime | Python 3.12 |
| Build command | `pip install -r requirements.txt` |
| Start command | `python serve.py` |
| Health check | `/healthz` |
| Persistent volume mount | `/data` |
| Instances / replicas | 1 |

Set these environment variables in the hosting dashboard, not in a committed file:

```text
CAFE_NAME=Your Cafe Name
CAFE_CURRENCY=INR
CAFE_TIMEZONE=Asia/Kolkata
CAFE_TAX_PERCENT=0
CAFE_DATA_DIR=/data
CAFE_DEMO=1
CAFE_ADMIN_USER=admin
CAFE_ADMIN_PASSWORD=<your own unique password of at least 16 characters>
APP_PUBLIC_URL=https://<your actual assigned hostname>
PORT=8080
```

Replace angle-bracket placeholders with actual values. `APP_PUBLIC_URL` is the exact HTTPS origin: no page path or query string. On Render, `RENDER_EXTERNAL_URL` is used automatically when `APP_PUBLIC_URL` is unset. On other hosts set `APP_PUBLIC_URL` yourself after generating the domain, then redeploy.

Initially deploy a demo. When it works, change `CAFE_DEMO` to `0` and restart to begin a separate empty real database on the same persistent volume. This does not convert synthetic history into real sales. Currency and timezone are fixed for each existing database.

### Railway as an alternative to Render

Connect your GitHub repository to a Railway service, attach a volume at `/data`, and configure the variables above. Use its public networking controls to generate a domain targeting port 8080, then set `APP_PUBLIC_URL` to that HTTPS origin and redeploy. The included Dockerfile provides the server start command. Ensure the mounted volume is writable by container user UID 10001; if it is not, use Railway's documented volume-permissions configuration. Do not solve a permission error by moving the database to temporary storage. See [Railway volumes](https://docs.railway.com/volumes) and the provider's current deployment UI.

### Render configuration

Create a Web Service from the GitHub repository. Choose Python 3 and the build/start commands in the table, or choose Docker to use the included Dockerfile. Attach a persistent disk at `/data` and set `CAFE_DATA_DIR=/data`. A persistent disk requires a paid service according to [Render's disk documentation](https://render.com/docs/disks). Set the staff password before deployment. Leave `APP_PUBLIC_URL` unset to use Render's assigned URL automatically. A custom domain requires updating `APP_PUBLIC_URL` to that exact domain.

### Docker on another server

The Dockerfile installs dependencies, copies only the runtime files, runs as a non-root user, and starts Waitress. Mount a private persistent volume at `/data` writable by UID 10001. Configure a reverse proxy with HTTPS and set `APP_PUBLIC_URL` to the address users will open. Forward its requests to container port 8080 while preserving the original Host header. This setup requires server administration; the repository does not provision DNS, TLS certificates, or a reverse proxy.

## E. Verify the hosted application

1. Visit its HTTPS address. A username/password prompt should appear.
2. Sign in with the configured staff credentials.
3. Confirm whether the banner says demo or the badge says live register.
4. Save a demo bill. Check its receipt and the dashboard.
5. Restart or redeploy the service. Confirm that the bill is still there; this checks persistence.
6. Download a CSV and verify that it says `synthetic_demo` in demo mode.
7. Only switch to real use after checking storage, backups, and the project's stated limitations.

## F. Backups and updates

From the project's environment run:

```powershell
.\.venv\Scripts\python.exe backup_database.py
```

The script uses SQLite's backup API to make a consistent copy of the configured database in `exports/`. For a hosted service run it in the provider's shell with an output folder on persistent storage, for example `python backup_database.py --output-dir /data/backups`. Keep a second private copy outside the server. A backup on the same disk does not protect against loss of that disk. CSV reports are not a full database backup.

To restore, stop the app, preserve the current database separately, and restore a known-good backup as `cafe.sqlite3` (or `demo.sqlite3`) in the configured data directory. Restore to a clean directory without stale WAL/SHM sidecar files, keep the matching currency/timezone settings, restart, and check receipts and totals. Practice restoration using a separate test environment first.

After code changes, run tests, review the changes, commit to GitHub, and redeploy using the same volume. Do not scale this SQLite starter across multiple independent servers. Migrate to a shared database such as PostgreSQL before that change.

## G. Troubleshooting

| Symptom | Check |
|---|---|
| `requirements.txt` not found | Confirm it is at repository root. If an outer folder was uploaded, reupload its contents or point Root Directory to that exact folder. |
| `No module named flask` | Install dependencies with the same Python executable used to run the app. |
| Port 8080 already used locally | Stop the other server or run `python app.py --demo --port 8081`. |
| Public hosting password error | Configure a unique password of at least 16 characters. |
| `Open the configured website address` | Open the exact domain in `APP_PUBLIC_URL`; ensure the proxy preserves Host. |
| Save returns 403 | Use the app from its configured HTTPS origin; do not submit from another domain. |
| Database permission error | Check the volume mount and ownership for the server's user. |
| Sales disappear after redeploy | The database was not written to a persistent volume. Correct storage before recording more sales. |
| Forecast not ready | The real register needs at least 35 completed calendar days. Use demo mode for learning. |
| Browser says a bill's save is uncertain | Retry that same locked bill. Do not collect payment again or start another copy. |
| No CSV download on a locked-down browser | Allow downloads for your app's origin. |

The project is prepared for deployment; it does not create a hosting account or public URL automatically.
