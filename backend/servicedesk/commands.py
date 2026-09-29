"""Explicit, non-destructive initialization and local demonstration data."""
import click
import secrets
from datetime import timedelta
from .models import db, User, Ticket, Comment, Activity, Article, now


def register_commands(app):
    @app.cli.command('init-db')
    def init_db():
        """Create missing tables. Existing records are preserved."""
        db.create_all()
        click.echo('Database tables are ready.')

    @app.cli.command('create-admin')
    @click.option('--name', prompt=True)
    @click.option('--email', prompt=True)
    @click.password_option()
    def create_admin(name, email, password):
        """Create an administrator without installing demo accounts."""
        import re
        if not 12 <= len(password) <= 128:
            raise click.ClickException('Password must contain 12–128 characters.')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email.strip()) or len(email) > 254:
            raise click.ClickException('Enter a valid email.')
        if not 2 <= len(name.strip()) <= 100:
            raise click.ClickException('Name must contain 2–100 characters.')
        email = email.strip().lower()
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException('Email already exists.')
        user = User(name=name.strip(), email=email, role='admin', department='IT')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo('Administrator created.')

    @app.cli.command('seed-demo')
    def seed_demo():
        """Seed sample data only into an empty user database; print generated credentials."""
        if db.session.scalar(db.select(db.func.count()).select_from(User)):
            raise click.ClickException('Database already has users. Demo seeding requires an empty database.')
        people = [('Sangeetha', 'admin@deskflow.local', 'admin', 'IT Operations'),
                  ('Arjun Rao', 'agent@deskflow.local', 'agent', 'IT Support'),
                  ('Meera Shah', 'employee@deskflow.local', 'employee', 'Finance'),
                  ('Vikram Patel', 'employee2@deskflow.local', 'employee', 'People Operations')]
        users, credentials = [], []
        for name, email, role, department in people:
            password = secrets.token_urlsafe(14)
            user = User(name=name, email=email, role=role, department=department)
            user.set_password(password)
            db.session.add(user)
            users.append(user)
            credentials.append((email, password))
        db.session.flush()
        samples = [
            ('VPN disconnects during client calls', 'Network', 'High', 'In Progress', 5),
            ('Request access to finance reporting', 'Access', 'Medium', 'Open', 3),
            ('Laptop battery drains within an hour', 'Hardware', 'Medium', 'Waiting on User', 27),
            ('Outlook fails to sync shared mailbox', 'Email', 'High', 'In Progress', 10),
            ('Install approved design software', 'Software', 'Low', 'Open', 2),
            ('Conference room display not detected', 'Hardware', 'Medium', 'Resolved', 45),
            ('Unable to connect to office Wi-Fi', 'Network', 'Critical', 'Open', 1),
            ('Password reset after account lockout', 'Access', 'High', 'Closed', 51),
            ('Spreadsheet application crashes on launch', 'Software', 'Medium', 'Resolved', 70),
            ('New starter equipment request', 'Hardware', 'Low', 'Open', 7),
            ('Email delivery delay to vendor', 'Email', 'Medium', 'Waiting on User', 19),
            ('Printer reports paper jam', 'Hardware', 'Low', 'Closed', 110),
        ]
        from .api import PRIORITIES
        for index, (title, category, priority, status, age) in enumerate(samples):
            created = now() - timedelta(hours=age)
            completed = status in ('Resolved', 'Closed')
            ticket = Ticket(title=title, description=f'{title}. The issue is affecting my daily work. Please investigate and let me know the next steps. This is sample demonstration data.',
                            category=category, priority=priority, status=status, requester_id=users[2 + index % 2].id,
                            assignee_id=users[1].id if status != 'Open' else None,
                            created_at=created, updated_at=created + timedelta(minutes=30),
                            due_at=created + timedelta(hours=PRIORITIES[priority]),
                            resolved_at=created + timedelta(hours=2) if completed else None,
                            resolution='Configuration corrected and functionality verified with the requester.' if completed else '')
            db.session.add(ticket)
            db.session.flush()
            db.session.add(Activity(ticket_id=ticket.id, actor_id=ticket.requester_id, message='Ticket created.', created_at=created))
            if status != 'Open':
                db.session.add(Comment(ticket_id=ticket.id, author_id=users[1].id, body='I am reviewing this request. Please share the exact error message if the issue occurs again.', created_at=created + timedelta(minutes=20)))
                db.session.add(Activity(ticket_id=ticket.id, actor_id=users[1].id, message=f'Demo ticket initialized as {status}.', created_at=created + timedelta(minutes=30)))
        articles = [
            ('Troubleshoot a VPN connection', 'Network', '1. Confirm your internet connection works without the VPN.\n2. Restart the approved VPN client.\n3. Check whether your password has recently changed.\n4. Record the exact error and time of the failure.\n5. Raise a Network ticket if it continues. Never share your password or one-time code.'),
            ('Request application access', 'Access', 'Include the application name, your department, the business reason, and the access level required. Attach manager approval if your organization requires it. The support team verifies approval before granting access.'),
            ('Report a suspicious email', 'Email', 'Do not open attachments or follow links. Use your organization’s approved phishing-report button if available. Raise an Email ticket with the sender and received time. Do not paste passwords or confidential message content into the ticket.'),
            ('Help us resolve your ticket faster', 'Other', 'Describe what you expected and what happened instead. Include steps to reproduce the problem, the error message, device details, and when it started. Add a screenshot after removing sensitive information. Choose Critical only when a major service is unusable.'),
        ]
        for title, category, body in articles:
            db.session.add(Article(title=title, category=category, body=body))
        db.session.commit()
        click.echo('\nDemo data created. Save these generated passwords privately:\n')
        for email, password in credentials:
            click.echo(f'{email}    {password}')
        click.echo('\nThese passwords are displayed once. Admin can reset other accounts in People.')
