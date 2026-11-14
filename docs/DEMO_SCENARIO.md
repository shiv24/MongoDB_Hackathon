# Demo scenario: Northstar customer exports

Synthetic hackathon example. These requirements describe a fictional product, not a deployed security system.

## Product
Northstar is a B2B customer operations workspace. Build its customer export screen for workspace administrators. The screen lives inside an existing admin console with a compact navigation rail and a clear page header. Use an understated ivory surface, dark forest-green navigation and restrained green action buttons. Avoid a solid green page background for this demo.

## Required experience
- Show a customer table with customer name, company, email, account status and created date.
- Include search, account-status filtering and a date-range filter. Show a visible summary of the active filters and the number of matching customers.
- The primary action is “Export filtered customers”. It applies to the current workspace and all matching rows, not just the visible page.
- Include an export configuration area with format fixed to CSV and an explicit list of the allowed columns: customer name, company, email, account status and created date.
- Show a confirmation state that names the workspace, filter summary, row count, included fields and CSV format before export begins.
- Include pending, ready, failed and empty-result states in the implementation brief. Disable export for an empty result and explain how to change filters.
- Display a recent export activity list with requester, time, workspace, row count and status. Use clearly fictional example names in the preview.

## Security and engineering requirements
- Derive the tenant/workspace from the authenticated server session. Never trust a client-supplied tenant identifier as authorization.
- Require workspace administrator export permission on the server. Hiding the button is insufficient; ordinary members see an explanation that an administrator is required.
- Enforce an allowlist of exported fields. Exclude password hashes, authentication tokens, payment details, private support notes and internal risk scores, even if those fields exist on the record.
- Write an audit event for export requests and outcomes, with actor, tenant, filter summary, allowed columns, row count and timestamp. Never put exported row contents or secrets into the audit event.
- An implementation must validate permissions and filters on the server and use existing project authentication and job infrastructure if available. No repository snapshot has been supplied, so do not invent file paths, service names or endpoint names.
- The generated HTML preview is an inert illustration. Label the preview data as sample data and do not claim authentication, filtering, downloads, audit persistence or server permissions are operational.

## Acceptance criteria
1. The prompt explicitly requires session-derived tenant isolation and server-side export authorization.
2. The prompt lists the five allowed columns and explicitly excludes sensitive fields.
3. The export respects the active filters across all matching rows in the authorized workspace.
4. Confirmation makes the scope visible before export.
5. Audit guidance includes metadata but excludes row contents and secrets.
6. Empty, denied, pending, ready and failed states are addressed.
7. The preview clearly marks its sample data and uses a readable hierarchy, table, filter controls, export summary and activity list.

## Presenting the demo
1. Open the shared brain and show the named demo source plus the three demo decisions.
2. Use the built-in example: “Build the Northstar customer export screen using our demo spec and team decisions.”
3. Show the additional constraints in the generated prompt: session-derived tenant, allowlisted fields, server permissions, active filters and audit metadata. Open the evidence cards.
4. Copy the prompt for an agent, or generate the optional visual preview. Explain that the preview is illustrative; acceptance checks are requirements, not executed tests.
5. Give one specific correction and approve it at project scope. Repeat the request to show the lesson when relevant. Allow Atlas indexing time before the repeat.

Run `python scripts/seed_demo_scenario.py` with the local server on port 8018 to add the sample records without resetting the database. Matching records are reused. Do not claim that a synthetic example establishes production security.
