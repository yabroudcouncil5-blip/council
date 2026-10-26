# Production handoff

The repository contains the application, migration history, service unit, Nginx template, cron schedule, and backup/restore scripts. A deployment owner must still perform the external steps below on the target VPS:

1. Install Python, PostgreSQL client/server, Nginx, and systemd.
2. Create the `yabroud` Linux user and PostgreSQL database.
3. Copy the repository to `/srv/yabroud`, create `.venv`, and install `requirements.txt`.
4. Create `.env` with a long secret, `DJANGO_DEBUG=0`, PostgreSQL connection values, and `DATABASE_URL` for backup scripts.
5. Run `manage.py migrate`, `collectstatic`, and `seed_yabroud`.
6. Install and enable `deploy/yabroud.service` and the cron entries.
7. Install the Nginx file with the real domain and issue a TLS certificate.
8. Verify `/health/`, login, complaint submission/tracking, private media denial, staff workflow, and public publication.
9. Run `collectstatic --noinput`, then `backup.sh`, restore into a separate database, and record the result.

Do not expose `/media/` directly. Serve private files only through an authorization-checked Django view.
