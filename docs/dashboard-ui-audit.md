# Dashboard UI/UX audit — 5 November 2026

## Shared redesign

The dashboard now uses one compact form layout across model pages. The shared
fieldset and row templates provide named layout classes instead of relying on
legacy Django CSS selectors that did not match Unfold's rendered structure.

- Tajawal is served locally and used by the overview, model pages and reports.
- Card headers use 10 px vertical padding; fields use 5 px label gaps and
  38 px text controls. Related fields share rows where useful and stack on mobile.
- Checkboxes remain 17 × 17 px and switches 34 × 20 px. Text-input width and
  height rules explicitly exclude boolean, hidden and file inputs.
- Readonly data renders as plain text. Complaint history is a compact table with
  Arabic stage names, public message, actor and timestamp.
- Sidebar labels precede consistently sized SVG icons. Account and theme menus
  open into the viewport; logout remains visible and keyboard accessible.
- Lists use consistent table density and contain horizontal scrolling inside
  their own table area. Rich-text toolbars wrap without overlapping their controls.
- Overview, reports and staff tasks use the same neutral panels and theme tokens.
- User, department, council settings, executive member, news and page forms have
  clearer field grouping. Department members use searchable selection.

## Complaint detail

Assignment, review and evidence tables have been replaced by compact responsive
record forms. Django formset management fields, hidden record IDs and dynamic
add/remove controls are preserved. Staff action notes include evidence previews
before the decision section. Files continue to use existing storage and access
rules; this redesign does not migrate or repair missing production media.

Old standalone assignment URLs redirect to the corresponding complaint using
the assignment's complaint ID. The old split workspace also forwards to the
normal complaint list or detail. Department staff tasks now include assignments
to their department even when an individual officer is not selected.

## Functional bugs corrected during the audit

- Role and department selection now persist during the admin's deferred save.
  The old form only applied them on a direct save with commit=True.
- Role choices use a styled select; department choices use compact checkboxes.
  The active control no longer receives full-width text-input styling.
- Account editing offers a simple password-change link instead of password hash
  metadata. Existing passwords are preserved, and view-only users see their role
  and departments without an unusable password-change link.
- Assignment deadlines now use a DateTimeField matching the native single input.
  Previously Unfold's SplitDateTimeField expected two values and rejected saves
  with “أدخل قائمة من القيم.”
- Legacy assignment redirects require admin login and no longer confuse an
  assignment ID with a complaint ID.

## Verification

Three specialist agents implemented and independently reviewed the staff forms,
complaint forms, overview and reports. Browser checks used an isolated SQLite
database and media directory; production records were not edited.

- The complete accounts/core/complaints/website suite passes (54 tests).
- Static collection and whitespace checks pass.
- An isolated route audit rendered 43 normal admin list/add/change URLs with the
  shared styles and font assets. Three retired assignment URLs returned redirects.
- Real Chrome checked overview, complaints, departments, users, staff creation
  and editing, council settings, executive members, page/news editors, staff tasks
  and reports at desktop 1440 px and mobile 390 px widths.
- The checked screens had no viewport overflow. Actual rendered Arabic glyphs
  were confirmed as Tajawal, and icon glyphs used their separate icon font.
- Browser interactions verified menu containment and logout hit-testing, mobile
  navigation, filters, theme switching and logout.
- A real mobile staff-create submission reopened the saved account with its
  selected role, department and active checkbox intact.
- A real complaint submission saved new assignment/review records and their
  native deadline, preserved existing evidence/history, and updated the event log.
- In-page staff evidence loaded successfully with real image dimensions.

The subsequent workflow audit replaces editable assignment/review controls with
one action panel and readonly history. It also requires a data-reconciliation
migration. See [complaint-workflow-audit.md](complaint-workflow-audit.md) for the
current behavior, deployment steps and 76-test verification.
