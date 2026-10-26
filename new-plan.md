MASTER DEVELOPMENT PROMPT
Yabroud Municipal Website & Complaints Management System
1. YOUR ROLE
You are a senior full-stack software engineer, software architect, database designer, UI/UX designer and security-focused developer.
Your task is to design and develop a complete, production-ready municipal website with an integrated public complaints management system for Yabroud City Council (بلدية يبرود) in Syria.
This is a real municipal platform intended for public use by residents and internal use by council employees.
You must understand the complete business requirements before beginning development.
IMPORTANT: This is NOT simply a complaints submission form.
It is a complete municipal website with:
1. A public-facing council website.
2. A complaints submission and tracking portal.
3. An internal complaints management system.
4. A multi-department assignment and action workflow.
5. A final review and approval process.
6. An administrative dashboard.
7. Department and employee management.
8. A website content management system (CMS).
9. Public publication of approved complaint resolutions.
10. Reporting and accountability features.
The platform must be designed professionally, securely and with an excellent Arabic user experience.

⸻

2. PROJECT STRATEGY
2.1 Initial Objective
The first version will be developed specifically for Yabroud City Council.
The priority is to create a complete, functional and reliable MVP without unnecessary complexity.
We do not yet know whether other councils will purchase the software.
Therefore:
DO NOT build a complicated multi-tenant SaaS platform.
DO NOT build subscription management or billing systems.
DO NOT build a central platform for managing multiple councils.
DO NOT spend time creating complicated licensing systems.
Instead, build one clean application that can be duplicated and installed independently for another council in the future.
2.2 Future Commercial Reuse
Although the first installation is for Yabroud, the software may later be sold to other municipalities.
The architecture must therefore support:
* One master codebase.
* Separate hosting for each council.
* Separate database for each council.
* Independent website content.
* Independent departments and officers.
* Independent complaints and evidence.
* Configurable council identity.
* Configurable complaint categories.
* Configurable website branding.
* Reusable installation and deployment procedures.
For example:
Yabroud Council:
* Its own hosting.
* Its own database.
* Its own domain.
* Its own website.
* Its own officers.
* Its own complaints.
Al-Nabk Council:
* Different hosting.
* Different database.
* Different domain.
* Different website content.
* Different departments.
* Different complaints.
Both installations should use the same application code.
Do not hard-code council-specific information into the application.
Use configuration settings and database records instead.
However, do not implement multi-tenancy in the MVP.

⸻

3. TECHNOLOGY STACK
Use a simple, maintainable Laravel architecture.
Recommended stack:
* Backend: Laravel.
* Frontend: Laravel Blade.
* Interactive components: Livewire.
* Styling: Tailwind CSS.
* Database: PostgreSQL or MySQL.
* Authentication: Laravel authentication.
* Permissions: Laravel policies/gates or a suitable role-permission package.
* File storage: Laravel Storage.
* Background processing: Laravel Queues.
* Testing: Pest or PHPUnit.
* Version control: Git.
Avoid introducing React, Next.js, microservices or a separate API unless there is a clear technical requirement.
The priority is maintainability, reliability and rapid development.
Use the latest stable versions compatible with the deployment environment.
Follow Laravel conventions and established software engineering practices.

⸻

4. APPLICATION STRUCTURE
The application must have three main areas.
AREA A: PUBLIC MUNICIPAL WEBSITE
Accessible without login.
AREA B: PUBLIC COMPLAINTS PORTAL
Allows residents to submit and track complaints without registration.
AREA C: INTERNAL ADMINISTRATIVE SYSTEM
Accessible only to authorised council employees.
The internal system must support multiple roles and departments.
All three areas belong to the same Laravel application.

⸻

5. PUBLIC MUNICIPAL WEBSITE
Create a professional, modern and responsive municipal website.
The website should represent Yabroud City Council.
5.1 Language and Layout
Arabic must be the primary language.
The entire interface must support right-to-left (RTL) layout.
Use appropriate Arabic fonts.
All public navigation, forms, buttons, validation messages and status labels must be in Arabic.
Structure the application to support English in the future, but do not spend significant development time translating the entire MVP.
The website must work properly on:
* Mobile phones.
* Tablets.
* Desktop computers.
Mobile usability is especially important.
5.2 Website Pages
Create the following pages.
Homepage
Include:
* Council logo and name.
* Main navigation.
* Hero section.
* Introduction to Yabroud City Council.
* Latest news and announcements.
* Municipal services.
* Quick access to submit a complaint.
* Quick access to track a complaint.
* Contact information.
* Footer.
About the Council
Include editable content describing:
* Council information.
* Responsibilities.
* Municipal services.
* Organisational information.
Departments
Display council departments.
Each department can have:
* Name.
* Description.
* Contact details.
* Services provided.
News and Announcements
Create a news management system.
Each article should support:
* Title.
* Content.
* Featured image.
* Publication date.
* Draft/published status.
Only authorised users can create and publish news.
Municipal Services
Create a page listing municipal services.
For the MVP, these can be informational pages.
Do not build complex online service applications.
Contact Page
Include:
* Council address.
* Telephone numbers.
* Email address.
* Working hours.
* Location map, if configured.
Complaints Page
Provide clear options to:
* Submit a new complaint.
* Track an existing complaint.
* View approved published resolutions.
Suggestions
Allow residents to submit general suggestions for improving municipal services.
For the MVP, suggestions may use a simplified submission form and separate administrative list.
They must not interfere with the complaints workflow.

⸻

6. WEBSITE CONTENT MANAGEMENT SYSTEM
The council must be able to update website content without modifying source code.
Create an administrative CMS.
The CMS should allow authorised administrators to manage:
* Homepage content.
* News.
* Announcements.
* Informational pages.
* Department descriptions.
* Contact information.
* Website logo.
* Website colours.
* Homepage banners.
* Uploaded images.
Keep the CMS simple.
Do not build a complicated drag-and-drop website builder.
A structured content editor is sufficient.

⸻

7. PUBLIC COMPLAINT SUBMISSION
Residents must be able to submit complaints without registering or logging in.
This is a fundamental requirement.
7.1 Complaint Form
Create the following fields.
Field	Requirement
Complaint title	Required
Complaint description	Required
Full name	Optional
Phone number	Optional
Email address	Optional
Complaint category	Optional
Neighbourhood/location	Optional
Address details	Optional
Photos	Optional
Submission date	Automatic
Complaint reference	Automatic
The complaint description must support Arabic text.
Do not require residents to provide personal information.
7.2 Photo Uploads
Allow multiple photographs to be uploaded.
Implement:
* File type validation.
* File size limits.
* Secure storage.
* Unique filenames.
* Protection against malicious uploads.
* Controlled access to original files.
Supported formats should include common image formats such as JPEG, PNG and WebP.
Define sensible configurable limits.
Do not automatically publish submitted photographs.
7.3 Complaint Reference Number
Every complaint must receive a unique reference number.
Example:
YBC-2026-000001
YBC-2026-000002
YBC-2026-000003
The reference must be generated safely without duplication, including when multiple complaints are submitted simultaneously.
The reference should remain unchanged throughout the complaint lifecycle.
7.4 Private Tracking Code
In addition to the reference number, generate a separate unpredictable tracking code.
The reference number identifies the complaint.
The private tracking code authorises access to the resident’s private tracking page.
Do not allow anyone to access private complaint details simply by guessing sequential reference numbers.
Store tracking credentials securely.
Show the tracking information immediately after successful submission.
If the resident does not provide contact details, clearly explain that they must save their reference and private tracking code.
7.5 Submission Confirmation
After successful submission, display:
* Confirmation message.
* Complaint reference number.
* Private tracking code.
* Submission date.
* Link to the tracking page.
The confirmation must be easy to understand in Arabic.
7.6 Initial Complaint Status
Every new complaint starts with:
Submitted / تم الاستلام
The complaint is then available to the complaint review team.

⸻

8. COMPLAINT MANAGEMENT WORKFLOW
This is the most important part of the entire application.
The workflow must be implemented carefully.
8.1 Main Workflow
The normal workflow is:
Resident submits complaint.
↓
System creates complaint.
↓
Complaint enters initial review queue.
↓
Review team examines complaint.
↓
Review team assigns complaint to one or more departments.
↓
Departments investigate and record actions.
↓
Departments submit their work for final review.
↓
Review team evaluates the actions.
↓
Review team either:
1. Returns work to the same department.
2. Assigns additional work to another department.
3. Approves completion and closes the complaint.
↓
Approved public resolution becomes available.

⸻

9. INITIAL COMPLAINT REVIEW
Create a dedicated review dashboard.
Only authorised review team members and administrators can access it.
9.1 Review Queue
Display complaints awaiting initial review.
Include:
* Reference number.
* Complaint title.
* Category.
* Submission date.
* Location.
* Current status.
* Priority.
* Assigned departments, if any.
Allow searching, filtering and sorting.
9.2 Complaint Details
Reviewers must be able to see:
* Complete complaint description.
* Contact details, where provided.
* Uploaded photographs.
* Location information.
* Complaint history.
* Existing assignments.
* Internal notes.
9.3 Reviewer Actions
Reviewers can:
* Edit complaint category.
* Set priority.
* Add internal notes.
* Assign one or more departments.
* Review possible duplicate complaints.
* Request additional information where contact details exist.
Do not silently alter the resident’s original complaint description.
Preserve the original submission.
Any administrative correction must be recorded separately or included in the audit history.

⸻

10. MULTIPLE DEPARTMENT ASSIGNMENTS
This requirement is critical.
One complaint can be assigned to multiple departments simultaneously.
Do not design the database with only one department_id on the complaint record.
Instead, create a separate complaint assignments table.
10.1 Example
A resident submits a complaint about:
* A damaged road.
* A broken streetlight.
The reviewer assigns the complaint to:
1. Roads Department.
2. Electricity Department.
Both departments must receive independent assignments.
10.2 Independent Assignment Status
Each assignment must have its own:
* Department.
* Responsible officer, if assigned.
* Status.
* Priority.
* Assignment date.
* Target completion date.
* Internal notes.
* Department actions.
* Evidence.
* Completion report.
Example:
Department	Status
Roads Department	Completed, Awaiting Review
Electricity Department	In Progress
The overall complaint remains open.
10.3 Assignment History
Do not delete previous assignments when complaints are reassigned.
Preserve the full history of:
* Assigned departments.
* Assignment dates.
* Officers.
* Actions.
* Review decisions.
* Returned work.
* Reassignments.
This information is essential for accountability.

⸻

11. DEPARTMENT DASHBOARD
Every department must have its own working area.
Officers should only access complaints assigned to their department, subject to their permissions.
11.1 Department Complaint List
Display:
* Complaint reference.
* Title.
* Category.
* Priority.
* Assignment date.
* Deadline.
* Assignment status.
* Responsible officer.
Provide filters for:
* New assignments.
* In progress.
* Awaiting final review.
* Returned for further work.
* Completed.
* Overdue.
11.2 Department Actions
An authorised officer can:
* Open an assigned complaint.
* View relevant complaint information.
* Start working on the assignment.
* Add internal action notes.
* Upload evidence.
* Update progress.
* Record work completion.
* Write a public response.
* Submit the assignment for final review.
11.3 Internal Action Report
The internal report is visible only to authorised council staff.
It may contain:
* Work undertaken.
* Inspection findings.
* Technical details.
* Internal comments.
* Action dates.
* Supporting photographs.
* Documents.
11.4 Public Response
The department must have a separate field for a public-facing explanation.
Example:
“تم إصلاح الإنارة في الموقع المذكور وإعادة تشغيلها.”
This response must not automatically become public.
It requires approval by the review team.
11.5 Evidence
Allow officers to upload:
* Before photographs.
* After photographs.
* Supporting documents.
Evidence must be classified as internal or approved for publication.
Only explicitly approved evidence may become publicly visible.

⸻

12. FINAL REVIEW PROCESS
When a department submits its completed action report, the assignment enters the final review queue.
The review team must evaluate the work.
12.1 Three Main Review Decisions
Decision A: Return to Same Department
The reviewer determines that the work is incomplete or insufficient.
The reviewer must provide a reason.
Example:
“The repair has not been fully completed. Please provide additional evidence.”
The assignment returns to the same department.
Its status becomes:
Returned for Further Work / أعيد لاستكمال المعالجة
The department can record additional actions and resubmit.
Preserve all previous actions and review decisions.
Decision B: Assign to Another Department
The reviewer determines that another department must become involved.
The reviewer can select another department and create an additional assignment.
The original department’s history must remain intact.
Example:
The Roads Department discovers that the problem is caused by a water leak.
The reviewer assigns the complaint to the Water Department.
The reviewer must explicitly decide whether the original assignment is completed, remains active or is superseded.
Do not automatically erase or replace the original assignment.
Decision C: Approve and Close
The reviewer determines that the complaint has been satisfactorily addressed.
The reviewer can:
* Approve departmental actions.
* Approve or edit the public explanation.
* Select evidence for publication.
* Record the final resolution.
* Close the complaint.
* Publish the approved outcome.
Only authorised reviewers and administrators may approve closure.

⸻

13. FINAL REVIEW WITH MULTIPLE DEPARTMENTS
This requires special attention.
Each department’s work should be reviewed independently.
Example:
A complaint has two assignments.
Roads Department:
* Work completed.
* Final review approved.
Electricity Department:
* Work incomplete.
* Returned for further work.
The complaint must remain open because the Electricity Department still has outstanding work.
13.1 Closure Rule
A complaint can only be closed when:
1. All required assignments have been approved or formally marked as no longer required.
2. No active assignment remains unresolved.
3. An authorised reviewer records the final decision.
4. The public resolution has been approved.
The system must enforce this rule.
Do not allow a department officer to close the entire complaint.
13.2 Partial Approvals
The reviewer may approve one department’s work while another department continues working.
Approved departmental actions remain recorded.
The overall complaint remains in progress until final closure.

⸻

14. COMPLAINT STATUSES
Separate overall complaint statuses from individual department assignment statuses.
14.1 Overall Complaint Status
Use:
* Submitted.
* Under Review.
* Assigned.
* In Progress.
* Final Review.
* Completed.
* Closed Without Resolution.
Arabic translations:
* تم الاستلام
* قيد المراجعة
* تمت الإحالة
* قيد المعالجة
* قيد التحقق النهائي
* تمت المعالجة
* أغلقت دون معالجة
The system must not display a complaint as successfully completed if the problem was not resolved.
14.2 Assignment Status
Use:
* Assigned.
* In Progress.
* Submitted for Review.
* Returned for Further Work.
* Approved.
* Cancelled / Superseded.
The overall complaint status should be calculated or updated consistently based on assignment states and authorised review decisions.
Avoid contradictory statuses.
Use database transactions for critical workflow changes.

⸻

15. PUBLIC COMPLAINT TRACKING
Residents must be able to track complaints without creating accounts.
15.1 Tracking Form
Require:
* Complaint reference number.
* Private tracking code.
15.2 Tracking Page
Display:
* Complaint reference.
* Submission date.
* Complaint title.
* Category.
* General location.
* Current status.
* Last update.
* Approved public progress information.
* Final public resolution, when available.
* Approved public evidence, when available.
Do not expose internal notes, private contact information or unapproved evidence.
15.3 Tracking Timeline
Provide a simple timeline.
Example:
12 October — Complaint received.
13 October — Under review.
14 October — Assigned to relevant departments.
15 October — Work in progress.
18 October — Final review.
19 October — Completed.
The timeline must be generated from real recorded events.
Do not create artificial progress updates.

⸻

16. PUBLIC RESOLVED COMPLAINTS
Create a public page displaying approved completed complaints.
This page should demonstrate council activity and improve transparency.
Display:
* Complaint reference.
* Category.
* General location.
* Completion date.
* Approved public summary.
* Approved photographs, if available.
Allow filtering by:
* Category.
* Department.
* Date.
* Location.
16.1 Publication Rules
Not every completed complaint must be published.
The review team must explicitly approve publication.
Allow the reviewer to choose:
* Publish resolution publicly.
* Keep resolution accessible only through private tracking.
Never publish:
* Resident names.
* Phone numbers.
* Email addresses.
* Private internal notes.
* Unapproved photographs.
* Sensitive personal information.

⸻

17. USER ROLES
Implement role-based access control.
The MVP requires the following roles.
17.1 Council Super Administrator
Can:
* Manage users.
* Create departments.
* Assign employees.
* Manage permissions.
* Manage complaint categories.
* Configure council settings.
* Manage website content.
* View all complaints.
* View reports.
* Access audit records.
17.2 Complaint Reviewer
Can:
* View complaints.
* Review new submissions.
* Assign departments.
* Set priorities.
* Review department reports.
* Return assignments.
* Create additional assignments.
* Approve resolutions.
* Close complaints.
* Approve public publication.
17.3 Department Manager
Can:
* View complaints assigned to their department.
* Assign work to officers in their department.
* Monitor progress.
* Record departmental actions.
* Submit work for final review.
17.4 Department Officer
Can:
* Log in.
* View authorised assignments.
* Record actions.
* Upload evidence.
* Update progress.
* Submit work for review.
Cannot:
* Access unrelated departments’ complaints.
* Approve final complaint closure.
* Publish public resolutions.
* Manage system-wide settings.
17.5 Website Content Editor
Can:
* Create news.
* Edit informational pages.
* Upload website images.
* Manage authorised website content.
Cannot access complaint information unless separately authorised.
17.6 Multiple Roles
A user may have more than one role if authorised.
A user may also belong to multiple departments.
Permission checks must consider both the user’s role and department membership.
Do not rely solely on hiding buttons in the interface.
Enforce permissions on the server.

⸻

18. DEPARTMENT MANAGEMENT
The Council Super Administrator must be able to:
* Create departments.
* Edit department names.
* Add descriptions.
* Activate or deactivate departments.
* Assign managers.
* Assign officers.
* Remove department membership.
* View departmental workload.
Department names must not be hard-coded.
Examples of possible departments:
* Roads.
* Electricity.
* Water.
* Sanitation.
* Parks.
* Building and Planning.
These are examples only.
The administrator must be able to create the actual departments used by Yabroud Council.

⸻

19. ADMINISTRATIVE DASHBOARD
Create a clear Arabic dashboard.
19.1 Dashboard Statistics
Display:
* Total complaints.
* New complaints.
* Under review.
* Assigned complaints.
* In-progress complaints.
* Awaiting final review.
* Completed complaints.
* Overdue assignments.
19.2 Complaint Management Table
Provide:
* Search by reference number.
* Search by title.
* Filter by category.
* Filter by status.
* Filter by department.
* Filter by priority.
* Filter by date.
19.3 Complaint Details
Use a structured layout containing:
1. Complaint information.
2. Attachments.
3. Department assignments.
4. Department action reports.
5. Review decisions.
6. Public response.
7. Complaint timeline.
8. Internal activity history.
The interface must clearly distinguish internal information from public information.

⸻

20. PRIORITIES AND DEADLINES
Support four priority levels:
* Critical.
* High.
* Medium.
* Low.
Allow administrators to configure target response times.
Suggested initial values:
Critical: 4 hours.
High: 24 hours.
Medium: 3 days.
Low: 7 days.
These are example targets, not official council commitments.
Store deadlines on individual assignments.
Show overdue assignments in the dashboard.
For the MVP, dashboard warnings are sufficient.
Do not build a complicated escalation engine.

⸻

21. NOTIFICATIONS
Implement simple internal notifications.
Notify relevant staff when:
* A complaint is assigned to their department.
* An assignment is returned for further work.
* A department submits work for review.
* A complaint requires final review.
Notifications should appear in the internal dashboard.
Design notification delivery so SMS and email can be added later.
Do not make SMS integration a requirement for the MVP.

⸻

22. AUDIT HISTORY
Every significant administrative action must be recorded.
Examples:
* Complaint assigned.
* Department changed.
* Officer assigned.
* Status updated.
* Internal action recorded.
* Evidence uploaded.
* Assignment returned.
* Assignment approved.
* Complaint closed.
* Public response published.
Each audit record should contain:
* Acting user.
* Action type.
* Related complaint.
* Related assignment, if applicable.
* Timestamp.
* Relevant changes.
Audit records must not be editable by ordinary officers.

⸻

23. DATABASE DESIGN
Design a clean relational database.
Recommended core tables:
users
Employee accounts and authentication information.
roles
System roles.
permissions
Role and user permissions.
departments
Council departments.
department_user
Department memberships.
council_settings
Council identity and configuration.
pages
Public website content.
news
News and announcements.
complaint_categories
Configurable complaint categories.
complaints
Main complaint information.
Suggested fields:
* id
* reference_number
* tracking_token_hash
* title
* description
* complainant_name
* complainant_phone
* complainant_email
* category_id
* location
* priority
* status
* submitted_at
* closed_at
* created_at
* updated_at
complaint_assignments
Individual departmental assignments.
Suggested fields:
* id
* complaint_id
* department_id
* assigned_officer_id
* assigned_by
* status
* priority
* assigned_at
* due_at
* completed_at
* approved_at
* created_at
* updated_at
assignment_actions
Departmental work records.
Suggested fields:
* id
* assignment_id
* user_id
* internal_action
* public_message
* action_date
* created_at
* updated_at
complaint_attachments
Uploaded photographs and documents.
Include:
* Complaint or assignment relationship.
* Storage path.
* File type.
* Original filename.
* Uploading user, where applicable.
* Visibility classification.
* Publication approval.
complaint_reviews
Review decisions.
Include:
* Complaint.
* Assignment, where applicable.
* Reviewer.
* Decision.
* Reason.
* Timestamp.
complaint_status_history
Complaint status changes.
notifications
Internal notifications.
audit_logs
Administrative audit history.
complaint_publications
Approved public resolution content and publication status.
You may adjust this structure where technically appropriate.
Use foreign keys, indexes, constraints and migrations.
Do not create unnecessary tables.

⸻

24. SECURITY REQUIREMENTS
Security is essential because the system handles resident information and internal government operations.
Implement:
1. Secure authentication.
2. Password hashing.
3. Role-based permissions.
4. Server-side authorisation.
5. CSRF protection.
6. Input validation.
7. Safe file uploads.
8. Protection against SQL injection.
9. Protection against cross-site scripting.
10. Rate limiting on public forms.
11. Rate limiting on tracking attempts.
12. Secure session management.
13. HTTPS configuration.
14. Secure private file storage.
15. Audit logging.
16. Database backup procedures.
Use Laravel’s established security mechanisms.
Do not expose uploaded files through predictable public URLs unless they have been explicitly approved for publication.
Do not expose sensitive resident information through public APIs, logs or error messages.
Consider data retention and privacy requirements.

⸻

25. DESIGN REQUIREMENTS
The website must look like a professional municipal government website.
Avoid generic developer dashboards or unfinished Bootstrap-style interfaces.
25.1 Public Website
Design principles:
* Professional.
* Modern.
* Trustworthy.
* Accessible.
* Clear navigation.
* Mobile-first.
* Arabic RTL.
* Consistent typography.
* Clear complaint submission buttons.
25.2 Administrative Interface
The dashboard should have:
* Sidebar navigation.
* Clear status indicators.
* Search and filters.
* Readable complaint tables.
* Well-organised forms.
* Confirmation messages.
* Validation feedback.
* Responsive layouts.
Use consistent colours for statuses.
Do not rely on colours alone to communicate status.
25.3 Accessibility
Use semantic HTML, accessible form labels, keyboard navigation and sufficient contrast.
Aim for WCAG 2.2 AA accessibility where practical.

⸻

26. MVP FEATURES TO IMPLEMENT
The first release must include:
1. Public municipal website.
2. Arabic RTL design.
3. Website CMS.
4. Council configuration.
5. Complaint submission.
6. Optional resident contact details.
7. Multiple photograph uploads.
8. Unique complaint reference.
9. Private complaint tracking.
10. Complaint review dashboard.
11. Department management.
12. Officer accounts.
13. Multiple department assignments.
14. Department action reporting.
15. Internal and public response fields.
16. Evidence uploads.
17. Final review workflow.
18. Return to department.
19. Assignment to another department.
20. Partial departmental approvals.
21. Final complaint closure.
22. Controlled public publication.
23. Role-based permissions.
24. Basic reporting.
25. Audit history.
26. Internal notifications.

⸻

27. FEATURES NOT REQUIRED IN THE MVP
Do not spend development time implementing:
* Multi-tenant SaaS architecture.
* Subscription billing.
* Payment processing.
* Central licensing server.
* Multiple website themes.
* Visual workflow designer.
* Artificial intelligence features.
* AI complaint classification.
* Automated duplicate detection.
* SMS gateway integration.
* Mobile applications.
* Advanced GIS mapping.
* Complex analytics.
* External government integrations.
* Resident account registration.
These may be considered in later versions.

⸻

28. DEVELOPMENT PHASES
Develop the application incrementally.
Phase 1: Foundation
Implement:
* Laravel project setup.
* Database configuration.
* Authentication.
* Roles and permissions.
* Council settings.
* Department management.
* Basic Arabic admin layout.
Phase 2: Public Website
Implement:
* Homepage.
* About page.
* Departments.
* News.
* Services.
* Contact.
* CMS.
Phase 3: Complaint Submission
Implement:
* Public complaint form.
* Validation.
* File uploads.
* Reference generation.
* Private tracking credentials.
* Submission confirmation.
* Complaint tracking.
Phase 4: Internal Workflow
Implement:
* Review dashboard.
* Complaint assignment.
* Multiple departments.
* Department dashboard.
* Officer actions.
* Evidence uploads.
* Public response drafts.
Phase 5: Final Review
Implement:
* Final review queue.
* Return to department.
* Additional department assignment.
* Individual assignment approvals.
* Complaint closure rules.
* Public publication approval.
Phase 6: Reporting and Testing
Implement:
* Dashboard statistics.
* Search and filters.
* Internal notifications.
* Audit history.
* Automated tests.
* Security testing.
* Deployment documentation.

⸻

29. IMPORTANT BUSINESS RULES
These rules must be enforced throughout the application.
Rule 1: Residents can submit complaints without accounts.
Rule 2: Resident name, phone number and email are optional.
Rule 3: Every complaint receives a unique reference.
Rule 4: Private tracking requires an additional secret code.
Rule 5: Every complaint enters the review queue before department assignment.
Rule 6: One complaint can be assigned to multiple departments.
Rule 7: Every department assignment has an independent status.
Rule 8: Departments can record multiple actions.
Rule 9: Internal action reports are never automatically public.
Rule 10: Public responses require reviewer approval.
Rule 11: Department officers cannot close entire complaints.
Rule 12: Reviewers can return assignments to the same department.
Rule 13: Reviewers can create additional assignments for other departments.
Rule 14: Previous departmental actions must remain recorded.
Rule 15: Reviewers can approve departmental work independently.
Rule 16: The overall complaint cannot close while required assignments remain unresolved.
Rule 17: Only authorised reviewers can approve final closure.
Rule 18: Only approved information may be published.
Rule 19: Complaint tracking must not expose internal information.
Rule 20: All significant actions must be auditable.
Rule 21: Department officers must not access unrelated departmental work.
Rule 22: Council branding and departments must be configurable.
Rule 23: The application must remain reusable for another council without source-code changes.
Rule 24: The MVP must remain simple and maintainable.

⸻

30. REQUIRED AUTOMATED TESTS
Create automated tests covering critical functionality.
At minimum, test the following scenarios.
Scenario 1: Anonymous Complaint
A resident submits a complaint without name, phone number or email.
Expected result:
Complaint successfully created.
Reference and private tracking code generated.
Complaint appears in review queue.
Scenario 2: Multiple Department Assignment
Reviewer assigns one complaint to two departments.
Expected result:
Two independent assignments are created.
Both departments can access their own assignments.
Scenario 3: Department Action
An officer records an internal action and public response.
Expected result:
Action is saved.
Public response remains unpublished.
Scenario 4: Return for Further Work
Reviewer rejects an assignment.
Expected result:
Assignment returns to the department.
Rejection reason is recorded.
Previous actions remain available.
Scenario 5: Partial Approval
One department completes its work while another remains active.
Expected result:
Completed assignment can be approved.
Overall complaint remains open.
Scenario 6: Final Closure
All required assignments are approved.
Reviewer closes the complaint.
Expected result:
Complaint status changes to completed.
Approved public response becomes available according to publication settings.
Scenario 7: Unauthorised Access
Officer attempts to access another department’s complaint assignment.
Expected result:
Access denied.
Scenario 8: Public Privacy
Unauthorised visitor attempts to access private complaint details or internal evidence.
Expected result:
Access denied.
Scenario 9: Tracking Security
Visitor enters a valid complaint reference with an invalid tracking code.
Expected result:
Private tracking information is not disclosed.
Scenario 10: Independent Installation
Install the same codebase using a different database and council configuration.
Expected result:
The application displays the new council’s branding, departments and website content without source-code modification.

⸻

31. DEVELOPMENT INSTRUCTIONS FOR CODEX
Follow these instructions carefully.
Before Coding
1. Inspect the existing repository.
2. Identify the current technology stack.
3. Identify any existing code and functionality.
4. Do not overwrite working functionality unnecessarily.
5. Compare existing implementation against these requirements.
6. Identify missing components.
7. Produce a concise implementation plan.
8. Identify important architectural decisions.
If the repository is empty, initialise the recommended Laravel application.
If an existing implementation uses a different technology stack, explain the implications before proposing a major rewrite.
During Development
Work in small, logical stages.
For each stage:
1. Implement database changes.
2. Implement models and relationships.
3. Implement business logic.
4. Implement authorisation.
5. Implement interface components.
6. Add validation.
7. Add tests.
8. Run relevant tests.
9. Fix errors before proceeding.
Use clean, readable and maintainable code.
Follow Laravel conventions.
Use database transactions for complaint assignment, review and closure operations where multiple records must remain consistent.
Avoid unnecessary abstractions and overengineering.
After Each Phase
Provide:
* Features implemented.
* Files created or modified.
* Database migrations added.
* Tests completed.
* Remaining work.
* Any blockers or decisions required.
Do not claim that a feature is complete unless it has been implemented and verified.

⸻

32. DEPLOYMENT REQUIREMENTS
The application must support deployment to a standard VPS.
Provide:
* Installation instructions.
* Environment variable documentation.
* Database setup instructions.
* Migration commands.
* Storage configuration.
* Queue worker setup.
* Web server configuration guidance.
* HTTPS requirements.
* Backup guidance.
* Update instructions.
Use environment variables for installation-specific configuration.
Do not commit secrets or production credentials.
The same source code must be deployable to another council’s hosting environment.

⸻

33. DEFINITION OF DONE
The MVP is considered complete when:
1. Residents can browse the municipal website.
2. Council staff can manage website content.
3. Residents can submit anonymous complaints.
4. The system generates unique complaint references.
5. Residents can securely track their complaints.
6. Reviewers can examine submissions.
7. Reviewers can assign multiple departments.
8. Officers can record actions and upload evidence.
9. Reviewers can return work for further action.
10. Reviewers can assign additional departments.
11. Departmental work can be approved independently.
12. Complaints cannot be closed prematurely.
13. Reviewers can approve final resolutions.
14. Approved resolutions can be published publicly.
15. Internal information remains private.
16. User permissions are enforced.
17. Audit history is recorded.
18. The administrative dashboard works in Arabic.
19. Critical automated tests pass.
20. The application can be installed on another server using a different database and council configuration.

⸻

34. FINAL INSTRUCTIONS
Build this project as a real municipal application, not a prototype consisting of static pages.
Prioritise:
1. Correct complaints workflow.
2. Security and privacy.
3. Clear Arabic user experience.
4. Maintainable database design.
5. Simple administration.
6. Reliable departmental coordination.
7. Reusable application architecture.
8. Practical deployment.
Do not introduce complex SaaS infrastructure at this stage.
Do not simplify the multi-department complaint workflow into a single department field.
Do not allow officers to bypass final review.
Do not publish complaint information without approval.
Do not confuse internal departmental actions with public responses.
Do not implement fake functionality or static dashboards that are not connected to real data.
Use realistic seed data only for local development and testing.
STARTING TASK:
First, inspect the repository and create an implementation plan based on this specification.
Identify the database entities, application modules, user roles, workflow states and development sequence.
Then begin implementing Phase 1.
Proceed incrementally, testing each phase before moving to the next.
If an important requirement is ambiguous, state your proposed assumption and ask for clarification where the decision would materially affect security, data integrity or the complaints workflow.
The final objective is a complete Arabic municipal website and a reliable internal complaints management system for Yabroud City Council, built using a simple architecture that can later be reused by other councils.
