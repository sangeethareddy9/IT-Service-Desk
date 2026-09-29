# Validation report

Build date: 7 September 2026.

## Completed checks

| Check | Result |
| --- | --- |
| Python backend API integration tests | **15 passed** in 37.48 seconds |
| React production build | Passed with Vite 6.4.3 |
| Frontend npm dependency audit | 0 reported vulnerabilities, including development dependencies, at build time |
| Python source and launcher syntax compilation | Passed |
| Empty-database demo seeding | Passed: 4 users, 12 tickets, 4 knowledge articles |
| Non-destructive seed protection | Passed; refuses to seed when users already exist |
| Flask serving bundled frontend | Passed: index response 200 |
| Health route and missing API route | Passed: 200 / 404 |
| MySQL schema generation | All 8 model tables compiled with the MySQL dialect |
| ZIP integrity and required files | Verified during packaging |

## Automated test coverage

1. Authentication, CSRF and logout.
2. Employee ownership restrictions across tickets, dashboards and exports.
3. Full ticket lifecycle, required resolution and stale-version rejection.
4. Staff-only internal note privacy, including requester notifications.
5. Attachment upload, authorized download, file type checks and size rejection.
6. Admin user management, duplicate accounts and disabled-session invalidation.
7. Password changes invalidate other sessions.
8. SLA overdue calculation, search/filtering, pagination and CSV formula escaping.
9. Agents cannot take over another agent's assigned ticket.
10. Active ticket ownership prevents disabling an agent.
11. Knowledge-base permissions and updates.
12. Invalid inputs and disallowed status transitions.
13. Failed-login throttling.
14. Demo seeding preserves existing users.
15. Cookie and response security headers.

Tests execute the Flask application against isolated SQLite databases. They are not mocks
of API responses; they exercise database writes, authentication cookies and authorization.

## Limits

- A live MySQL server was unavailable. Schema compilation is **not** a live MySQL integration test.
  Follow MYSQL_SETUP.md and verify a full ticket workflow on your installed MySQL server.
- No Windows machine or interactive browser test was used. Windows batch files and Python
  launchers are included, and the Python launcher source compiled successfully.
- A clean automated setup run was attempted in the build environment but could not complete
  because its network approval was cancelled during dependency installation. Backend dependencies
  were available for the successful application tests. First setup on your laptop requires internet.
- The frontend compiled, but visual layout and browser interactions have not been manually verified.
- The dependency audit reported above covers npm packages, not Python packages or application penetration testing.
- No load test, malware scanner validation, business-hours SLA test or production deployment was performed.

Run the included tests again after making backend changes. Rebuild the frontend after JSX/CSS changes.
