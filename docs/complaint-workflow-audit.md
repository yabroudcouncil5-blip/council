# Complaint workflow audit — 6 November 2026

## Corrected causes

- Assignment, staff action, review and publication had different write paths.
  Some admin forms saved only an assignment/review row, leaving the complaint
  stage and public event history unchanged.
- Public tracking replaced a closed complaint's stage with “awaiting approval”
  when a separate publication flag was absent. This made it contradict the
  dashboard and hid the latest decision.
- Staff permission checks required a named officer even though assignments
  were department-level. Some reviewers could not see readonly history because
  inline permissions were checked without a complaint instance.
- The old evidence previews used raw media URLs that Django does not serve in
  production by default. Publication did not select and release proof together
  with the review decision.

## One action panel and one current stage

Open the normal complaint list and then the complaint details. The “الإجراء
التالي” panel provides actions appropriate to the user's role and the current
stage. Assignment and review records are readonly history; users do not edit a
second status field or use another workflow page.

| Action | Complaint stage in dashboard and public tracker | Details |
| --- | --- | --- |
| Resident submits | تم الاستلام | Reference and generic event are public. |
| Reviewer assigns a department | تمت الإحالة | Department staff see the case without choosing an officer. |
| Department starts work | قيد المعالجة | Internal notes are private. |
| Department sends its action and evidence | تم اتخاذ الإجراء، بانتظار الاعتماد | Proposed text and proof remain internal for review. |
| Reviewer approves and publishes | أغلقت بعد الاعتماد | Approved public summary and selected council proof are released together. |
| Reviewer returns to the same department | تمت الإحالة | Staff see the internal completion instructions. |
| Reviewer transfers to another department | أحيلت إلى قسم آخر | Previous open routing is cancelled; the new department receives the case. |
| Reviewer closes without action | أغلقت دون معالجة | An explicit public reason is required. |

`complaints/workflow.py` is the single write path for the action panel and legacy
API endpoints. Each valid action updates the complaint, assignment/review rows
and event history in one transaction. A stale form cannot overwrite a newer
action. A department officer cannot assign or approve cases, or act on a case
outside their department. Reviewers and supervisors can review the department's
notes and proof before confirming a final decision.

The public tracker uses the complaint's actual current stage and a chronological
event table. The last row contains the final public decision and inline proof.
There is no separate top status banner. An open result checks for updates every
30 seconds while visible; ordinary reloads and the JSON endpoint use the same
read-only tracking function. Lookup does not create history or alter the case.

## Evidence and privacy

- Staff and administrators can upload multiple images/PDFs through the same
  action panel. Author and council source are recorded automatically.
- Staff notes, reviewer notes, contact details and resident evidence are not
  copied into public tracking. Proposed staff text remains private until review.
- Approval requires a public summary, explicit review/publish confirmation and
  selection of the council files to release. Newly uploaded reviewer proof is
  included in that same confirmed publication.
- Reopening revokes publication and public proof access until another approval.
  Old proof is not preselected for the next review cycle.
- `/complaints/evidence/<id>/` serves inline files in production. Unpublished
  uploads require case access; selected published council files can be viewed
  anonymously. Preview images are resized to at most 960 px and compressed as
  WebP, while opening the evidence link preserves the original file.
- Selecting an existing file missing from storage blocks publication with an
  instruction to re-upload it. Code cannot recover files lost from ephemeral
  hosting; the complaint media directory still requires persistent storage.

## Existing records and deployment

Migration `complaints.0008_reconcile_workflow` repairs old review-only saves,
fills missing submission/current-stage history and respects later transfers or
staff actions. It does not publish historical private reasons or unapproved
evidence. A legacy closed case can publish its final summary/proof from the same
action panel. The website page-title migration records an existing Arabic label
so migration state matches the model.

Deploy code, run `python manage.py migrate --noinput`, then run
`python manage.py collectstatic --noinput`. Keep complaint media on persistent
storage and use the evidence endpoint for complaint-file previews.

## Verification

- 76 accounts/core/complaints/website tests pass, including 22 workflow cases.
- Tests cover every stage, public/dashboard agreement, reviewer attribution,
  department access, multiple departments, return/transfer/reopen, invalid file
  rollback, stale actions, readonly audit records, production file serving,
  multiple proofs, lightweight previews and historical record reconciliation.
- Schema/migration checks and whitespace checks pass.
- A real Chrome journey uses separate department staff and reviewer accounts:
  assign → start → submit proof → review → approve and publish. The dashboard
  and anonymous tracking API agree at each step, and the public page displays
  the final note and loaded proof on desktop and mobile without overflow.
- Browser and migration checks use an isolated database/media directory. This
  audit does not claim that the changes have been deployed to the Render site.
