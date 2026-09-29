# JSON API reference

Base URL for the bundled application: `http://127.0.0.1:5000/api`.
Authenticated endpoints require the session cookie. Every state-changing API request, including
login, requires `X-CSRF-Token` from `GET /auth/session`. The frontend handles both automatically.
Login and password changes return a replacement token; use the latest returned value.

Responses are JSON except attachment downloads and CSV exports. Error shape:

```json
{"error":"Human-readable explanation"}
```

Common statuses: 400 invalid input/CSRF, 401 login required, 403 forbidden,
404 missing or inaccessible resource, 409 duplicate/stale record, 413 request too large,
429 excessive failed logins, 500 unexpected server failure.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /health | Process health; does not verify database connectivity |
| GET | /auth/session | Current user or null, and CSRF token |
| POST | /auth/login | Sign in with email and password |
| POST | /auth/logout | Clear current session |
| POST | /auth/password | Change own password and revoke other sessions |
| GET | /meta | Categories, priorities, statuses, transitions, active staff |
| GET | /dashboard | Metrics scoped to the current user's visibility |
| GET | /tickets | Filtered paginated ticket list |
| POST | /tickets | Create a ticket for the current user |
| GET | /tickets/{id} | Ticket, permitted comments, activity, attachment metadata |
| PATCH | /tickets/{id} | Version-checked workflow/assignment update |
| POST | /tickets/{id}/comments | Add public reply or staff-only note |
| POST | /tickets/{id}/attachments | Upload one multipart file |
| GET | /attachments/{id} | Authorized download |
| GET | /tickets/export | Staff CSV export with the same filters |
| GET | /users | Admin list of users |
| POST | /users | Admin creates a user |
| PATCH | /users/{id} | Admin edits a user / resets password |
| GET | /notifications | Latest 100 notifications for signed-in user |
| POST | /notifications/read | Mark own notifications read |
| GET | /articles | Knowledge articles |
| POST | /articles | Staff creates an article |
| PATCH | /articles/{id} | Staff updates an article |

## Create a ticket

```json
{
  "title": "VPN disconnects during calls",
  "description": "The VPN disconnects every ten minutes. Restarting the client did not help.",
  "category": "Network",
  "priority": "High"
}
```

Title: 5–180 characters. Description: 10–10,000. Priority defaults to Medium.
The requester and deadline are assigned by the server; clients cannot choose another requester.

## List and filter

`GET /tickets?q=VPN&status=Open&priority=High&category=Network&scope=unassigned&page=1&per_page=12`

Filters are optional. `scope` may be `mine` (assigned to self), `unassigned`, or `overdue`.
Employees always remain restricted to their own requests. `per_page` is 1–100.

```json
{"items": [], "total": 0, "pages": 0, "page": 1}
```

## Update a ticket

Use the current `version` from the ticket response. An agent must claim an unassigned ticket
before changing its workflow. Admin can assign any active staff account.

```json
{"version": 1, "assignee_id": 2}
```

```json
{"version": 2, "status": "In Progress"}
```

```json
{"version": 3, "status": "Resolved", "resolution": "VPN client configuration corrected and verified."}
```

A resolution requires 10–10,000 characters. Allowed transitions are returned by `/meta`.
The API returns 409 if the version is missing, outdated, or changed by a concurrent transaction.
Refresh the ticket before reapplying a change; do not silently overwrite another agent's work.

## Replies and attachments

```json
{"body": "The connection is stable now. Thank you.", "internal": false}
```

Body: 1–10,000 characters. Internal notes require staff privileges and are excluded from
employee responses and requester notifications. Attachments use multipart field `file`.
Allowed extensions: PDF, PNG, JPG/JPEG and UTF-8 TXT. Each file may be 5 MB maximum;
a ticket may have 10 files. Downloads always require ticket access and force attachment disposition.

## User creation / password change

```json
{"name":"Example User","email":"user@example.com","department":"Finance","role":"employee","password":"UseYourOwnLongPassword"}
```

Passwords must contain 12–128 characters and are stored as Werkzeug password hashes.
Role: `employee`, `agent`, or `admin`. User responses never include the hash.

```json
{"current_password":"CurrentPrivatePassword","new_password":"NewPrivatePassword"}
```

## Knowledge articles

Create/update requires `title` (5–180), `category`, and `body` (20–20,000).
Articles are plain text. React escapes their content; raw HTML is not executed.

## Login throttling

Failures are stored in the database using hashes of the email and client IP keys.
The window is 15 minutes: 10 failures per email or 50 per client IP block further attempts.
Expired rows are removed during login. Behind a reverse proxy, configure trusted client-IP
handling deliberately; the application does not blindly trust forwarded headers.
