# Troubleshooting

## `python` is not recognized

Use `py -3` on Windows. Your Python Launcher can work even when the `python` PATH entry does not.
The supplied batch files and setup instructions use `py`.

## Setup cannot download a dependency

The first setup needs an internet connection to Python's package repository. Check the error,
connection and proxy settings, then rerun setup. Do not delete your database to fix a download problem.

## Demo seed says the database already has users

This is an intentional protection. Your existing records remain in place. Start the app and use
your saved credentials. For an additional admin, from `backend/` run:

```powershell
.\.venv\Scripts\python.exe -m flask --app app create-admin
```

Choose a new email. Do not delete a database that contains work you need to keep.

## Lost demo password

If another administrator can sign in, they can reset the password in People. If this is your
own local installation and no administrator can sign in, use the local `create-admin` command
above to make another administrator. You must have local machine/database access for this operation.
Generated passwords are not shipped in the ZIP and cannot be recovered from a hash.

## Port 5000 is already in use

Close an earlier DeskFlow terminal with Ctrl+C, or stop the application you know is using that port.
Do not terminate unfamiliar processes. For development you can choose another Flask port, but
update the Vite proxy accordingly. The packaged launcher expects port 5000.

## Browser opens but cannot connect

Leave the START_WINDOWS terminal open and inspect its errors. Try entering
`http://127.0.0.1:5000` manually. If the server immediately exits, confirm setup completed.

## Blank or stale frontend after editing

Run `npm ci` and `npm run build` inside `frontend/`, then restart the Python server and refresh.
`start.py` serves `frontend/dist/`; it does not compile JSX on demand.
Use `npm run dev` at port 5173 for live editing.

## Session expired / CSRF validation error

Refresh the page, sign in again and retry. If another tab logged out or changed the password,
its newer session token may make an older tab stale. Repeated login failures trigger a 15-minute limit.

## MySQL access denied / cannot connect

- Confirm the MySQL Windows service is running.
- Test `mysql -h 127.0.0.1 -u deskflow -p it_service_desk` first.
- Check user host, port, database name and password.
- URL-encode password punctuation in DATABASE_URL.
- Check that `.env` is named exactly `.env`, not `.env.txt`.
- Restart the backend after changing `.env`.

## Tables not found

From `backend/`, run:

```powershell
.\.venv\Scripts\python.exe -m flask --app app init-db
```

Ensure `.env` points to the intended database before initializing.

## Cannot disable an agent

Reassign that agent's unresolved tickets to active staff first. The app prevents leaving active
work assigned to a disabled account. You cannot disable or demote your own administrator account.

## Cannot mark a ticket resolved

An agent must own the ticket. Move Open → In Progress (or Waiting on User) first, then choose
Resolved and enter a resolution summary of at least 10 characters. Employees cannot resolve tickets.

## Attachment rejected

Use a real PDF, PNG, JPG/JPEG or UTF-8 TXT, at most 5 MB. Renaming an executable to `.png` will
not pass the signature check. A ticket can hold at most ten attachments.
