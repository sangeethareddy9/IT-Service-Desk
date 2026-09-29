"""Database entities. Dates are stored as UTC without timezone for MySQL parity."""
from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat() + 'Z' if value else None


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')
    department = db.Column(db.String(100), nullable=False, default='General')
    active = db.Column(db.Boolean, nullable=False, default=True)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    @property
    def is_active(self):
        return self.active

    def get_id(self):
        return f'{self.id}:{self.session_version}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public(self):
        return dict(id=self.id, name=self.name, email=self.email, role=self.role,
                    department=self.department, active=self.active)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Open')
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    requester = db.relationship(User, foreign_keys=[requester_id])
    assignee = db.relationship(User, foreign_keys=[assignee_id])
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now, index=True)
    due_at = db.Column(db.DateTime, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime)
    resolution = db.Column(db.Text, nullable=False, default='')
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version}

    def public(self):
        return dict(id=self.id, number=f'IT-{self.id:05d}', title=self.title,
                    description=self.description, category=self.category, priority=self.priority,
                    status=self.status, requester=self.requester.public(),
                    assignee=self.assignee.public() if self.assignee else None,
                    created_at=iso(self.created_at), updated_at=iso(self.updated_at),
                    due_at=iso(self.due_at), resolved_at=iso(self.resolved_at),
                    overdue=self.status not in ('Resolved', 'Closed') and self.due_at < now(),
                    resolution=self.resolution, version=self.version)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship(User)
    body = db.Column(db.Text, nullable=False)
    internal = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    def public(self):
        return dict(id=self.id, author=self.author.public(), body=self.body,
                    internal=self.internal, created_at=iso(self.created_at))


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actor = db.relationship(User)
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    def public(self):
        return dict(id=self.id, actor=self.actor.name, message=self.message, created_at=iso(self.created_at))


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(100), nullable=False, unique=True)
    size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    def public(self):
        return dict(id=self.id, filename=self.filename, size=self.size, created_at=iso(self.created_at))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    def public(self):
        return dict(id=self.id, ticket_id=self.ticket_id, message=self.message,
                    read=self.read, created_at=iso(self.created_at))


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    body = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)

    def public(self):
        return dict(id=self.id, title=self.title, category=self.category, body=self.body, updated_at=iso(self.updated_at))


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now, index=True)
