# Connect your installed MySQL Server 8.0

The quick-start demo uses SQLite. MySQL uses the same application code through SQLAlchemy.
A live MySQL server was not available in the build environment; run the connection and workflow
checks below on your laptop before describing your installation as MySQL-tested.

## 1. Create the database and a dedicated application user

Open PowerShell:

```powershell
mysql -u root -p
```

Enter your MySQL root password privately when prompted. Run the following in the MySQL shell,
replacing the example password with a strong private value:

```sql
CREATE DATABASE it_service_desk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'deskflow'@'localhost' IDENTIFIED BY 'REPLACE_WITH_YOUR_PRIVATE_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES
ON it_service_desk.* TO 'deskflow'@'localhost';
EXIT;
```

`CREATE` and `INDEX` are for initial table creation. For a deployment, separate schema migration
credentials from runtime credentials and reduce runtime privileges after initialization.
Do not use the root account as the application's database user.

Verify this dedicated login before editing Python settings:

```powershell
mysql -h 127.0.0.1 -u deskflow -p it_service_desk
```

Then `EXIT;`.

## 2. Edit backend/.env

If it does not exist, copy `backend/.env.example` to `backend/.env`.
Replace the `DATABASE_URL` line with:

```dotenv
DATABASE_URL=mysql+pymysql://deskflow:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:3306/it_service_desk?charset=utf8mb4
COOKIE_SECURE=false
```

Do not leave two active `DATABASE_URL` lines. `127.0.0.1` and port `3306` assume the default local server.
Use the actual port if your MySQL installation uses a different one.

Special password characters must be URL encoded. To safely encode without putting the password
in shell history, run this in PowerShell and enter the password at the hidden prompt:

```powershell
py -3 -c "from getpass import getpass; from urllib.parse import quote; print(quote(getpass('Database password: '), safe=''))"
```

Copy that output into the password portion of the connection string. The output is still a
credential: do not share it in screenshots. `PyMySQL` and `cryptography` are included to support
MySQL 8 authentication methods.

## 3. Initialize MySQL

Stop the running app first. From the project root:

```powershell
py -3 scripts/setup.py --demo
```

This creates the tables in the configured MySQL database and generates fresh demo credentials.
The earlier SQLite data remains in `backend/instance/servicedesk.db`; it is not imported or deleted.
If MySQL already contains users, omit `--demo` and sign in with an existing account.

For a new database without sample records, use:

```powershell
py -3 scripts/setup.py
cd backend
.\.venv\Scripts\python.exe -m flask --app app create-admin
```

Then return to the root and launch `START_WINDOWS.bat`.

## 4. Verify the connection and persistence

Using the MySQL shell:

```sql
USE it_service_desk;
SHOW TABLES;
SELECT id, name, email, role FROM user;
SELECT id, title, status, priority FROM ticket ORDER BY id DESC LIMIT 5;
```

Never query or share password hashes for a project screenshot.

In the app, create a ticket as Employee, assign it as Admin, resolve it as Agent,
and restart the app. Verify that the same ticket, replies and resolution remain available.

`schema_mysql.sql` is a reference DDL generated from the actual SQLAlchemy models.
The recommended initializer is `flask --app app init-db`; choose one initialization method.
