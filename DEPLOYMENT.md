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

Use PostgreSQL, a long random `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, HTTPS, secure cookies, Gunicorn, and Nginx. Keep complaint uploads under `media/` private. Django serves only saved council logos at `/media/council/logos/` in production, including on Render. The Nginx example can serve that directory directly. Use persistent media storage so uploaded logos survive redeploys; if an existing file was lost, upload it again. Serve attachments only through an authorization-checked Django view when that feature is enabled. Run migrations before release and create a backup before every migration.

On Render, the application automatically adds `RENDER_EXTERNAL_HOSTNAME` to
`ALLOWED_HOSTS`. For custom domains, set `DJANGO_ALLOWED_HOSTS` to a comma-separated
list of hostnames without `https://` or paths. To resolve a 400 on the existing
deployment immediately, set `DJANGO_ALLOWED_HOSTS=yabroud-council.onrender.com`
in Render's Environment settings and redeploy. Keep `DJANGO_DEBUG=0`.

The root `.python-version` pins Render to Python 3.12, which is compatible with
Django 4.2. Python 3.14 is incompatible with this Django version and causes admin
template rendering to fail. Remove any Render `PYTHON_VERSION` environment
variable so the repository pin takes effect; that variable overrides the file.

Recommended cron jobs:

```text
*/5 * * * * /path/.venv/bin/python /path/manage.py notify_overdue
*/10 * * * * /path/.venv/bin/python /path/manage.py health_report
0 2 * * * pg_dump "$DATABASE_URL" > /secure/backups/yabroud-$(date +\%F).sql
```

Test a restore before launch. Never commit `.env`, database passwords, production media, or backups.

## Admin theme

The admin uses `django-unfold==0.67.0`, pinned for compatibility with the existing
Django 4.2 application. Install the updated requirements and run `collectstatic`
on deployment to publish Unfold's fonts, styles, and scripts. All model admins,
including users and groups, inherit Unfold's `ModelAdmin`. Arabic navigation is
configured in `UNFOLD` in `config/settings.py`. Reports are at `/staff/reports/`.

## Council logo

In the admin, open **بيانات البلدية**, edit the council record (or create it), upload **شعار البلدية**, and save. The logo appears in the public website header. Clear the image to restore the default mark. Install requirements and run migrations before using this field.

## Dashboard and public forms

Run `python manage.py collectstatic --noinput` during deployment to publish the dashboard RTL styles and shared public form styles. The dashboard uses Noto Sans Arabic with Tahoma as a fallback. Tracking is embedded on the homepage and also available at `/complaints/track/`; it uses only the complaint reference, for both existing and new complaints. Tracking forms submit to `/?reference=...#tracking` and show the result or error immediately below the homepage form. They use read-only GET requests so lookups work without CSRF cookies, including behind HTTPS proxies. The JSON tracking endpoint also supports GET. Complaint submission and dashboard writes remain POST requests protected by CSRF. Public tracking returns the status and public timeline, without personal details, complaint descriptions, titles, or attachments. Legacy tracking hashes remain stored for compatibility but are no longer used.

## Website content editor

Council staff can format text and insert images in **صفحات الموقع** and **الأخبار والإعلانات**. The toolbar supports headings, font sizes, bold/italic/underline, lists, alignment, links, and image uploads (PNG/JPEG/WebP, up to 5 MB and 20 million pixels). Images are stored under `media/website/images/` and served at `/website-images/`; this directory needs persistent storage in production.

Install requirements, run migrations, and run `collectstatic --noinput` before deploying. Quill 2.0.3 assets and its BSD license are included locally; editor operation does not require a third-party CDN or API key. Page formatting is sanitized on save and display. Existing plain-text content keeps its paragraph breaks. Custom published pages are available at `/pages/<slug>/`, with a “view on site” link in the admin. The existing homepage layout is maintained in templates.
