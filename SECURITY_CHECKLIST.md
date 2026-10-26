# Stages 7–9 acceptance checklist

- Production secret and debug checks pass.
- HTTPS, secure session cookies, CSRF, and HSTS are enabled in production.
- Public endpoints expose only approved fields.
- Private media is not served through predictable public paths.
- Role and department permissions are tested server-side.
- Upload type and size validation is active.
- Tracking-code failures return no complaint details.
- Audit records and publication decisions are retained.
- Dashboard reports are restricted to staff.
- Low-bandwidth pages are server-rendered and paginated.
- `health_report` succeeds in the deployment environment.
- PostgreSQL backup and restore have been tested.
