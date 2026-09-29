# Start here, Sangeetha

This is your **IT Service Desk and Ticket Management System**, branded **DeskFlow**.
It includes the complete React source, Flask backend, database models, tests, documentation,
and a built frontend. The built frontend means you can run the first demo without npm.

## First run on your Windows laptop

1. Extract the ZIP completely. Use a **new folder**, such as
   `Desktop\it-service-desk-complete`. Keep your earlier project folder as it is.
2. Open the extracted `it-service-desk` folder.
3. Double-click **SETUP_WINDOWS.bat**. Internet is needed to install Python packages.
4. When it finishes, **save the generated email/password pairs privately**.
   Each demo installation gets different passwords; there is no shared default password.
5. Double-click **START_WINDOWS.bat**. Keep that terminal window open.
6. Your browser should open at **http://127.0.0.1:5000**.
7. Log in with `admin@deskflow.local` and its generated password.

**PowerShell alternative** — open the extracted project folder in VS Code,
then run in its terminal:

```powershell
py -3 scripts/setup.py --demo
py -3 scripts/start.py
```

Your `py` command already works. You do not need to fix the `python` PATH command
or activate a virtual environment for this setup.

Setup creates a local SQLite database so you can immediately explore the project.
**MySQL is fully configurable through the backend connection string**; follow
`docs/MYSQL_SETUP.md` when you are ready to connect your installed MySQL Server 8.0.
Switching databases does not transfer existing demo records automatically.

## Demo accounts

| Email | Role | What to try |
| --- | --- | --- |
| admin@deskflow.local | Admin | Dashboard, assign tickets, People, reports |
| agent@deskflow.local | Agent | Claim an unassigned ticket, reply, resolve |
| employee@deskflow.local | Employee | Create a ticket, attach evidence, track updates |
| employee2@deskflow.local | Employee | Verify that one employee cannot see another's tickets |

Passwords appear in the setup terminal **once**. Save them before closing it.
Use My account to change a password. Admin can reset another user's password in People.

## Next time

Only run **START_WINDOWS.bat** (or `py -3 scripts/start.py`). Do not seed again.
Data remains in `backend/instance/`. Stop the server with **Ctrl+C**.

## Files to read next

- `README.md`: features, structure, development commands.
- `docs/MYSQL_SETUP.md`: MySQL database and connection setup.
- `docs/PROJECT_GUIDE.md`: architecture, database relationships, viva questions, demo script.
- `docs/API.md`: API endpoints and request examples.
- `docs/TEST_REPORT.md`: validation performed and its limits.
- `docs/TROUBLESHOOTING.md`: startup, login, database and port fixes.

This ZIP is a new implementation based on your project topic and Python/React/MySQL stack.
It does not include files copied from your laptop. You can use it as a complete learning
and portfolio project and customize the branding, demo data, and workflows yourself.
