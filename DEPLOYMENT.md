# Django deployment

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_yabroud
.venv/bin/python manage.py runserver
```

## Production

Use PostgreSQL, a long random `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, HTTPS, secure cookies, Gunicorn, and Nginx. Keep `media/` private; production URL routing deliberately does not expose `/media/`. Serve attachments only through an authorization-checked Django view when that feature is enabled. Run migrations before release and create a backup before every migration.

Recommended cron jobs:

```text
*/5 * * * * /path/.venv/bin/python /path/manage.py notify_overdue
*/10 * * * * /path/.venv/bin/python /path/manage.py health_report
0 2 * * * pg_dump "$DATABASE_URL" > /secure/backups/yabroud-$(date +\%F).sql
```

Test a restore before launch. Never commit `.env`, database passwords, production media, or backups.
