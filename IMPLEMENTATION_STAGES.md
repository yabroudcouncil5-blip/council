# Yabroud Municipal Website and Complaints System

## Technology and deployment decision

Build a single Django application with PostgreSQL, Django Templates, HTMX, and Tailwind CSS. Use Django authentication, groups, permissions, model policies, private media storage, and management commands scheduled by cron. Deploy the application and web server on one VPS with PostgreSQL on the same VPS or a managed PostgreSQL service. Do not introduce Redis, Celery, a separate frontend, microservices, resident accounts, SMS, AI, or multi-tenant SaaS in the MVP.

`new-plan.md` remains the complete requirements source. This document is the implementation sequence and acceptance plan.

## Stage 0 — Project foundation

Create the Django project and establish the runtime baseline.

Deliverables:

- Python environment and pinned dependencies
- Django project and applications for core, website, complaints, workflow, accounts, and reporting
- PostgreSQL connection and environment configuration
- Base Arabic RTL template with responsive Tailwind styling
- Development, test, staging, and production settings
- `.env.example`, local setup guide, and Git workflow
- Health endpoint and initial pytest configuration

Acceptance: a clean checkout installs, connects to PostgreSQL, runs migrations, loads a seed council configuration, serves an Arabic page, and runs tests.

## Stage 1 — Accounts, roles, departments, and council settings

Implement the internal security and configuration foundation.

Deliverables:

- Staff login, logout, password reset, secure sessions, and rate limiting
- Super Administrator, Complaint Reviewer, Department Manager, Department Officer, and Website Content Editor roles
- Multiple roles per user and multiple department memberships
- Department creation, activation, descriptions, managers, and officers
- Council name, logo, colours, contact details, working hours, and map settings
- Server-side Django permissions and policies
- Append-only audit event model and initial audit recording

Acceptance: unauthorized users are denied; officers can access only authorized department work; council identity is database-driven; role and membership changes are audited.

## Stage 2 — Public municipal website and CMS

Build the professional public Arabic website.

Deliverables:

- Homepage with council identity, introduction, news, services, contact details, and complaint shortcuts
- About, departments, municipal services, news, contact, complaints, and suggestions pages
- CMS for structured pages, announcements, news drafts/published states, department descriptions, images, logo, colours, and homepage content
- Editor permissions and publication workflow
- Mobile-first Arabic RTL layouts with accessible labels, keyboard navigation, and clear status communication

Acceptance: authorized editors can update content without code; drafts remain private; public pages work on mobile and low-speed connections.

## Stage 3 — Complaint submission, files, references, and tracking

Implement the public complaint portal without resident registration.

Deliverables:

- Complaint form for title, description, optional identity/contact, category, neighbourhood, address, and photos
- Multiple JPEG, PNG, and WebP uploads with size/type validation and private storage
- Secure unique reference such as `YBC-2026-000001`
- Separate unpredictable tracking code stored securely
- Arabic confirmation page with reference, code, date, and tracking link
- Tracking page with safe status, approved timeline entries, and approved public updates
- Recovery request process for lost tracking details
- Separate suggestions submission and administrative list
- Public-form rate limiting and duplicate-submit protection

Acceptance: an anonymous resident can submit and track a complaint; invalid tracking codes reveal nothing; original complaint text is immutable; optional upload failure does not lose the complaint.

## Stage 4 — Review queue and multi-department workflow

Implement the core council process using real relational records.

Deliverables:

- Review queue with search, filters, sorting, priority, category, date, and status
- Complaint detail with original content, contact data, private files, history, notes, and assignments
- Separate `complaint_assignments` model allowing many departments per complaint
- Assignment officer, manager, status, priority, target date, actions, evidence, and history
- Review actions for categorization, priority, duplicate, out-of-scope, additional information, and assignment
- Transaction-protected assignment and status changes
- Department dashboard restricted by department membership

Acceptance: one complaint can be assigned to multiple departments simultaneously; each assignment is independent; previous assignments and changes remain visible in history.

## Stage 5 — Department actions, evidence, deadlines, and notifications

Implement department work and operational accountability.

Deliverables:

- Officer and manager work areas
- Multiple internal action records per assignment
- Separate internal report and public-response draft fields
- Evidence uploads classified as internal or publication-candidate
- Assignment statuses: Assigned, In Progress, Submitted for Review, Returned, Approved, Cancelled/Superseded
- Configurable Critical, High, Medium, and Low target times
- Overdue dashboard warnings and deadline management commands
- In-app notifications for assignment, return, submission, and final review
- Cron-compatible notification and deadline jobs without Redis/Celery

Acceptance: officers can record work and submit it without publishing; evidence remains private by default; deadlines belong to individual assignments; notifications are recorded and visible to authorized staff.

## Stage 6 — Final review, partial approval, closure, and publication

Implement governance over completion and public transparency.

Deliverables:

- Final review queue and review decisions with required reasons
- Return to the same department without deleting prior work
- Additional assignment to another department without replacing existing history
- Independent approval of each department assignment
- Closure guard requiring all required assignments to be approved or formally ended
- Final public response editor and evidence selection
- Private, tracked-only, and public publication options
- Public resolved-complaints page with category, department, date, and location filters
- Redaction and unpublish capability

Acceptance: unresolved required work blocks closure; partial approval leaves the overall complaint open; officers cannot close or publish; public output excludes names, contact details, internal notes, and unapproved evidence.

## Stage 7 — Reporting, audit, and operational monitoring

Make performance and accountability visible.

Deliverables:

- Dashboard counts for all complaint statuses and overdue assignments
- Search and permission-aware filters/exports
- Department workload and resolution-time reporting
- Complete audit history for assignment, status, officer, action, evidence, review, closure, and publication changes
- Structured application logs without resident secrets
- Health checks for application, database, storage, scheduler, and backups
- Cron-based daily checks for overdue work, notification failures, and backups
- Privacy scan for published content

Acceptance: authorized users can monitor workload and accountability; ordinary officers cannot edit audit records; monitoring does not log complaint content or credentials.

## Stage 8 — Security, accessibility, low-bandwidth, and pilot testing

Validate the system with realistic council cases.

Required automated scenarios:

1. Anonymous complaint submission
2. Two independent department assignments
3. Department action with private/public fields
4. Return for further work
5. Partial approval while another department remains active
6. Final closure after all required work is approved
7. Unauthorized department access denied
8. Public privacy boundary enforced
9. Invalid tracking code discloses nothing
10. Independent installation with different council configuration

Additional checks:

- Upload security and private file access
- CSRF, XSS, SQL-injection, session, and rate-limit testing
- Password and permission review
- Arabic RTL, keyboard, contrast, and mobile testing
- Slow 3G test with compressed assets and text-first pages
- Text submission succeeds when optional upload fails
- Backup restore drill and incident-response rehearsal

Acceptance: critical security and privacy findings are closed; pilot departments complete real workflows; a restore succeeds; low-bandwidth and accessibility checks pass.

## Stage 9 — VPS deployment and launch

Deploy and operate one council installation safely.

Deliverables:

- Gunicorn and Nginx configuration
- PostgreSQL migration and backup procedures
- Private media directory and permissions
- Cron configuration for deadlines, notifications, backups, and cleanup
- HTTPS and secure-cookie configuration
- Environment-variable documentation with no committed secrets
- Monitoring contacts, incident runbook, support ownership, and upgrade procedure
- Staged launch followed by controlled expansion to all departments

Acceptance: the same code can be installed with another database and council configuration without source changes; backups and restore are verified; production ownership is assigned.

## Stage gates

- Do not begin Stage 3 until authentication, permissions, departments, and council settings pass tests.
- Do not begin Stage 4 until the public submission and tracking journey passes privacy tests.
- Do not begin Stage 6 until independent multi-department assignments and assignment histories work.
- Do not launch until Stage 8 security, accessibility, low-bandwidth, pilot, and restore checks pass.

## Definition of done

The MVP is complete only when the public municipal website and CMS work, anonymous complaints can be securely tracked, multiple departments can work independently, reviewers can return/approve/close according to the rules, approved resolutions can be published, permissions and audit history are enforced, critical tests pass, private evidence is protected, the system works on slow connections, and a second independent council configuration can run from the same codebase.
