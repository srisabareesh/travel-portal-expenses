# Travel Portal — Backend

Django + Django REST Framework backend for the ONSITE TRAVEL
MANAGEMENT & EXPENSE SETTLEMENT PORTAL.

## Development

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations --check   # must report: No changes detected
python manage.py migrate                  # applies pending migrations (additive only)
python manage.py test                     # full backend test suite
python manage.py runserver
```

## Production

Production configuration is environment-driven via
`config.settings_production` (extends `config.settings`).
The development settings remain the default and are never
weakened.

Required environment variables:

| Variable | Purpose |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings_production` |
| `DJANGO_SECRET_KEY` | 50+ random characters, kept secret |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated public host names (required; startup fails without it) |

Optional environment variables:

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | `1` only for troubleshooting; enables DEBUG and disables HTTPS hardening |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins |
| `DJANGO_SQLITE_PATH` | Absolute path for the SQLite database (persistent storage / backup target) |
| `DJANGO_STATIC_ROOT` | Static file collection directory |
| `DJANGO_MEDIA_ROOT` | Uploaded document/receipt storage (private; serve only through authenticated endpoints) |
| `DJANGO_ERROR_LOG_PATH` | Error log file location |
| `DJANGO_LOG_LEVEL` | Root log level (default `INFO`) |

Production checklist:

```bash
export DJANGO_SETTINGS_MODULE=config.settings_production
export DJANGO_SECRET_KEY="<50+ random characters>"
export DJANGO_ALLOWED_HOSTS="portal.example.com"
export DJANGO_CORS_ALLOWED_ORIGINS="https://portal.example.com"
export DJANGO_SQLITE_PATH="/var/lib/travel-portal/db.sqlite3"

python manage.py migrate          # additive migrations only; never resets data
python manage.py collectstatic --noinput
python manage.py check --deploy   # additional deployment checks
```

Operational notes:

- **Backups**: back up the SQLite database file (and
  `MEDIA_ROOT`) on a schedule; stop writes or use SQLite's
  backup API/`VACUUM INTO` for a consistent copy.
- **Historical data**: migrations are additive and never
  convert legacy travel types, statuses or employee IDs.
- **Documents**: uploaded files live under `MEDIA_ROOT`;
  do not serve this directory publicly without adding
  authentication in front of it.
- **Secrets**: never commit `.env` files; supply secrets
  through the deployment environment.
