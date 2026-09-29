"""JSON API. Authorization is enforced here, independently of the UI."""
import csv
import hashlib
import io
import re
import secrets
from datetime import timedelta
from functools import wraps
from pathlib import Path
from flask import Blueprint, abort, current_app, jsonify, request, session, send_file
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from .models import db, User, Ticket, Comment, Activity, Attachment, Notification, Article, LoginAttempt, now

api = Blueprint('api', __name__)
PRIORITIES = {'Low': 72, 'Medium': 24, 'High': 8, 'Critical': 4}
CATEGORIES = ['Hardware', 'Software', 'Network', 'Access', 'Email', 'Other']
TRANSITIONS = {
    'Open': ['In Progress', 'Waiting on User'],
    'In Progress': ['Waiting on User', 'Resolved'],
    'Waiting on User': ['In Progress', 'Resolved'],
    'Resolved': ['Closed', 'Open'],
    'Closed': ['Open'],
}


def roles(*allowed):
    def wrapper(fn):
        @wraps(fn)
        @login_required
        def inner(*args, **kwargs):
            if current_user.role not in allowed:
                abort(403, 'You do not have permission for this action.')
            return fn(*args, **kwargs)
        return inner
    return wrapper


def data():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400, 'Send a JSON object.')
    return body


def string(body, key, low=1, high=100, default=None):
    value = body.get(key, default)
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        abort(400, f'{key.replace("_", " ").title()} must contain {low}–{high} characters.')
    return value.strip()


def choice(body, key, options, default=None):
    value = body.get(key, default)
    if not isinstance(value, str) or value not in options:
        abort(400, f'Invalid {key}.')
    return value


def password(body, key='password'):
    value = body.get(key)
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        abort(400, 'Use a password of 12–128 characters.')
    return value


def email_value(body):
    value = string(body, 'email', high=254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        abort(400, 'Enter a valid email address.')
    return value


def ticket_query():
    stmt = db.select(Ticket)
    if current_user.role == 'employee':
        stmt = stmt.where(Ticket.requester_id == current_user.id)
    return stmt


def get_ticket(tid):
    ticket = db.session.get(Ticket, tid)
    if not ticket or (current_user.role == 'employee' and ticket.requester_id != current_user.id):
        abort(404, 'Ticket not found.')
    return ticket


def record(ticket, message, notify=True):
    db.session.add(Activity(ticket_id=ticket.id, actor_id=current_user.id, message=message))
    if notify:
        for uid in {ticket.requester_id, ticket.assignee_id} - {None, current_user.id}:
            db.session.add(Notification(user_id=uid, ticket_id=ticket.id, message=f'IT-{ticket.id:05d}: {message}'))


@api.get('/health')
def health():
    return jsonify(status='ok')


@api.get('/auth/session')
def auth_session():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(32)
    return jsonify(user=current_user.public() if current_user.is_authenticated else None, csrf=session['csrf'])


@api.post('/auth/login')
def sign_in():
    body = data()
    email = email_value(body)
    raw_password = body.get('password', '')
    if not isinstance(raw_password, str) or len(raw_password) > 128:
        abort(400, 'Invalid password.')
    cutoff = now() - timedelta(minutes=15)
    db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
    keys = [hashlib.sha256(v.encode()).hexdigest() for v in [f'ip:{request.remote_addr}', f'email:{email}']]
    for key, limit in zip(keys, [50, 10]):
        count = db.session.scalar(db.select(db.func.count()).select_from(LoginAttempt).where(LoginAttempt.key == key))
        if count >= limit:
            db.session.commit()
            abort(429, 'Too many login attempts. Wait 15 minutes and try again.')
    user = db.session.scalar(db.select(User).where(User.email == email))
    if not user or not user.active or not user.check_password(raw_password):
        db.session.add_all([LoginAttempt(key=key) for key in keys])
        db.session.commit()
        abort(401, 'Incorrect email or password.')
    db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.key == keys[1]))
    db.session.commit()
    session.clear()
    login_user(user)
    session.permanent = True
    session['csrf'] = secrets.token_hex(32)
    return jsonify(user=user.public(), csrf=session['csrf'])


@api.post('/auth/logout')
@login_required
def sign_out():
    logout_user()
    session.clear()
    return jsonify(ok=True)


@api.post('/auth/password')
@login_required
def change_password():
    body = data()
    old = body.get('current_password')
    if not isinstance(old, str) or len(old) > 128 or not current_user.check_password(old):
        abort(400, 'Current password is incorrect.')
    user = current_user._get_current_object()
    user.set_password(password(body, 'new_password'))
    user.session_version += 1
    db.session.commit()
    login_user(user)
    session['csrf'] = secrets.token_hex(32)
    return jsonify(ok=True, csrf=session['csrf'])


@api.get('/meta')
@login_required
def meta():
    return jsonify(categories=CATEGORIES, priorities=list(PRIORITIES), statuses=list(TRANSITIONS), transitions=TRANSITIONS,
                   agents=[u.public() for u in db.session.scalars(db.select(User).where(User.active.is_(True), User.role.in_(['agent', 'admin'])).order_by(User.name))]
                   if current_user.role != 'employee' else [])


def filtered_tickets():
    stmt = ticket_query()
    for key in ('status', 'priority', 'category'):
        value = request.args.get(key)
        if value:
            stmt = stmt.where(getattr(Ticket, key) == value)
    term = request.args.get('q', '').strip()[:180]
    if term:
        escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        conditions = [Ticket.title.ilike(f'%{escaped}%', escape='\\'), Ticket.description.ilike(f'%{escaped}%', escape='\\')]
        numeric = term.upper().removeprefix('IT-')
        if numeric.isdigit():
            conditions.append(Ticket.id == int(numeric[:9]))
        stmt = stmt.where(or_(*conditions))
    if request.args.get('scope') == 'mine':
        stmt = stmt.where(Ticket.assignee_id == current_user.id)
    if request.args.get('scope') == 'unassigned':
        stmt = stmt.where(Ticket.assignee_id.is_(None))
    if request.args.get('scope') == 'overdue':
        stmt = stmt.where(Ticket.due_at < now(), Ticket.status.notin_(['Resolved', 'Closed']))
    return stmt.order_by(Ticket.updated_at.desc(), Ticket.id.desc())


@api.get('/tickets')
@login_required
def tickets():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('per_page', 12, type=int)
    if page is None or page < 1 or size is None or not 1 <= size <= 100:
        abort(400, 'Invalid pagination.')
    result = db.paginate(filtered_tickets(), page=page, per_page=size, error_out=False)
    return jsonify(items=[t.public() for t in result.items], total=result.total, pages=result.pages, page=page)


@api.post('/tickets')
@login_required
def create_ticket():
    body = data()
    priority = choice(body, 'priority', PRIORITIES, 'Medium')
    ticket = Ticket(title=string(body, 'title', 5, 180), description=string(body, 'description', 10, 10000),
                    category=choice(body, 'category', CATEGORIES), priority=priority,
                    requester_id=current_user.id, due_at=now() + timedelta(hours=PRIORITIES[priority]))
    db.session.add(ticket)
    db.session.flush()
    record(ticket, 'Ticket created.')
    db.session.commit()
    return jsonify(ticket.public()), 201


@api.get('/tickets/<int:tid>')
@login_required
def ticket_detail(tid):
    ticket = get_ticket(tid)
    comments = db.select(Comment).where(Comment.ticket_id == tid)
    if current_user.role == 'employee':
        comments = comments.where(Comment.internal.is_(False))
    result = ticket.public()
    result.update(comments=[c.public() for c in db.session.scalars(comments.order_by(Comment.created_at, Comment.id))],
                  activity=[a.public() for a in db.session.scalars(db.select(Activity).where(Activity.ticket_id == tid).order_by(Activity.id.desc()))],
                  attachments=[a.public() for a in db.session.scalars(db.select(Attachment).where(Attachment.ticket_id == tid).order_by(Attachment.id))])
    return jsonify(result)


@api.patch('/tickets/<int:tid>')
@login_required
def update_ticket(tid):
    ticket = get_ticket(tid)
    body = data()
    if type(body.get('version')) is not int or body['version'] != ticket.version:
        abort(409, 'This ticket has changed. Refresh before saving.')
    is_staff = current_user.role in ('admin', 'agent')
    permitted = {'version', 'status', 'resolution'} | ({'priority', 'assignee_id'} if is_staff else set())
    if set(body) - permitted:
        abort(403, 'You cannot edit these fields.')
    changes = []
    if 'assignee_id' in body:
        aid = body['assignee_id']
        if aid is not None:
            if type(aid) is not int:
                abort(400, 'Invalid assignee.')
            assignee = db.session.get(User, aid)
            if not assignee or not assignee.active or assignee.role not in ('agent', 'admin'):
                abort(400, 'Choose an active agent or administrator.')
        if current_user.role == 'agent' and (aid != current_user.id or ticket.assignee_id not in (None, current_user.id)):
            abort(403, 'Agents can only claim unassigned tickets. Ask an admin to reassign.')
        if aid != ticket.assignee_id:
            ticket.assignee_id = aid
            changes.append('Assignment updated.')
    if is_staff and current_user.role == 'agent' and ticket.assignee_id != current_user.id:
        abort(403, 'Claim this ticket before updating it.')
    if 'priority' in body:
        priority = choice(body, 'priority', PRIORITIES)
        if priority != ticket.priority:
            ticket.priority = priority
            ticket.due_at = ticket.created_at + timedelta(hours=PRIORITIES[priority])
            changes.append(f'Priority changed to {priority}.')
    if 'status' in body:
        status = choice(body, 'status', TRANSITIONS)
        if status != ticket.status:
            allowed = TRANSITIONS[ticket.status] if is_staff else (['Closed', 'Open'] if ticket.status == 'Resolved' else ['Open'] if ticket.status == 'Closed' else [])
            if status not in allowed:
                abort(400, 'This status transition is not allowed.')
            if status == 'Resolved':
                ticket.resolution = string(body, 'resolution', 10, 10000)
                ticket.resolved_at = now()
            elif status == 'Open':
                ticket.resolved_at = None
                ticket.resolution = ''
                # Reopening retains the original SLA deadline rather than hiding breaches.
            ticket.status = status
            changes.append(f'Status changed to {status}.')
    if not changes:
        abort(400, 'No changes to save.')
    ticket.updated_at = now()
    for message in changes:
        record(ticket, message)
    db.session.commit()
    return jsonify(ticket.public())


@api.post('/tickets/<int:tid>/comments')
@login_required
def add_comment(tid):
    ticket = get_ticket(tid)
    body = data()
    internal = body.get('internal', False)
    if type(internal) is not bool:
        abort(400, 'Invalid internal note setting.')
    if internal and current_user.role == 'employee':
        abort(403, 'Employees cannot add internal notes.')
    comment = Comment(ticket_id=tid, author_id=current_user.id, body=string(body, 'body', 1, 10000), internal=internal)
    db.session.add(comment)
    ticket.updated_at = now()
    if not internal:
        record(ticket, 'A new reply was added.')
    db.session.commit()
    return jsonify(comment.public()), 201


@api.post('/tickets/<int:tid>/attachments')
@login_required
def upload_attachment(tid):
    ticket = get_ticket(tid)
    count = db.session.scalar(db.select(db.func.count()).select_from(Attachment).where(Attachment.ticket_id == tid))
    if count >= 10:
        abort(400, 'Maximum 10 attachments per ticket.')
    file = request.files.get('file')
    if not file or not file.filename:
        abort(400, 'Choose a file.')
    name = secure_filename(file.filename)[:200]
    extension = Path(name).suffix.lower()
    if extension not in ('.pdf', '.png', '.jpg', '.jpeg', '.txt'):
        abort(400, 'Allowed file types: PDF, PNG, JPG and TXT.')
    content = file.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        abort(400, 'File must be between 1 byte and 5 MB.')
    signatures = {'.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}
    if extension in signatures and not content.startswith(signatures[extension]):
        abort(400, 'File content does not match its extension.')
    if extension == '.txt':
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            abort(400, 'Text files must use UTF-8 encoding.')
    storage_name = secrets.token_hex(24) + extension
    path = Path(current_app.config['UPLOAD_FOLDER']) / storage_name
    path.write_bytes(content)
    attachment = Attachment(ticket_id=tid, uploader_id=current_user.id, filename=name, storage_name=storage_name, size=len(content))
    try:
        db.session.add(attachment)
        ticket.updated_at = now()
        record(ticket, f'Attachment added: {name}')
        db.session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return jsonify(attachment.public()), 201


@api.get('/attachments/<int:aid>')
@login_required
def download_attachment(aid):
    attachment = db.get_or_404(Attachment, aid)
    get_ticket(attachment.ticket_id)
    path = Path(current_app.config['UPLOAD_FOLDER']) / attachment.storage_name
    if not path.exists():
        abort(404, 'Attachment file is unavailable.')
    return send_file(path, as_attachment=True, download_name=attachment.filename, mimetype='application/octet-stream')


@api.get('/dashboard')
@login_required
def dashboard():
    rows = list(db.session.scalars(ticket_query()))
    active = [t for t in rows if t.status not in ('Resolved', 'Closed')]
    resolved = [t for t in rows if t.resolved_at]
    start = now().date() - timedelta(days=6)
    trend = [{'date': (start + timedelta(days=i)).isoformat(), 'created': 0, 'resolved': 0} for i in range(7)]
    for t in rows:
        for item in trend:
            item['created'] += int(t.created_at.date().isoformat() == item['date'])
            item['resolved'] += int(bool(t.resolved_at) and t.resolved_at.date().isoformat() == item['date'])
    return jsonify(total=len(rows), active=len(active), overdue=sum(t.due_at < now() for t in active),
                   unassigned=sum(t.assignee_id is None for t in active), resolved=len(resolved),
                   sla_met=round(100 * sum(t.resolved_at <= t.due_at for t in resolved) / len(resolved)) if resolved else None,
                   average_resolution_hours=round(sum((t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved) / len(resolved), 1) if resolved else None,
                   by_status={s: sum(t.status == s for t in rows) for s in TRANSITIONS},
                   by_category={s: sum(t.category == s for t in rows) for s in CATEGORIES}, trend=trend,
                   recent=[t.public() for t in sorted(rows, key=lambda t: t.updated_at, reverse=True)[:5]])


@api.get('/tickets/export')
@roles('admin', 'agent')
def export_csv():
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['Ticket', 'Title', 'Status', 'Priority', 'Category', 'Requester', 'Assignee', 'Created UTC', 'Due UTC'])
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value
    for t in db.session.scalars(filtered_tickets()):
        writer.writerow([safe(x) for x in [f'IT-{t.id:05d}', t.title, t.status, t.priority, t.category, t.requester.name,
                                          t.assignee.name if t.assignee else '', t.created_at, t.due_at]])
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name='service-desk-tickets.csv')


@api.get('/users')
@roles('admin')
def users():
    return jsonify([u.public() for u in db.session.scalars(db.select(User).order_by(User.name))])


@api.post('/users')
@roles('admin')
def create_user():
    body = data()
    user = User(name=string(body, 'name', 2, 100), email=email_value(body),
                role=choice(body, 'role', ['employee', 'agent', 'admin']), department=string(body, 'department', 1, 100, 'General'))
    user.set_password(password(body))
    db.session.add(user)
    db.session.commit()
    return jsonify(user.public()), 201


@api.patch('/users/<int:uid>')
@roles('admin')
def update_user(uid):
    user = db.get_or_404(User, uid)
    body = data()
    if set(body) - {'name', 'department', 'active', 'role', 'password'}:
        abort(400, 'Unsupported user field.')
    role = choice(body, 'role', ['employee', 'agent', 'admin'], user.role)
    active = body.get('active', user.active)
    if type(active) is not bool:
        abort(400, 'Invalid active setting.')
    if uid == current_user.id and (not active or role != 'admin'):
        abort(400, 'You cannot disable or demote your own administrator account.')
    if not active or role == 'employee':
        assigned = db.session.scalar(db.select(db.func.count()).select_from(Ticket).where(Ticket.assignee_id == uid, Ticket.status.notin_(['Resolved', 'Closed'])))
        if assigned:
            abort(400, 'Reassign this user’s active tickets before disabling or changing to Employee.')
    if 'name' in body:
        user.name = string(body, 'name', 2, 100)
    if 'department' in body:
        user.department = string(body, 'department', 1, 100)
    if 'password' in body:
        user.set_password(password(body))
        user.session_version += 1
    if role != user.role or active != user.active:
        user.session_version += 1
    user.role, user.active = role, active
    db.session.commit()
    if uid == current_user.id:
        login_user(user)
    return jsonify(user.public())


@api.get('/notifications')
@login_required
def notifications():
    stmt = db.select(Notification).where(Notification.user_id == current_user.id)
    rows = db.session.scalars(stmt.order_by(Notification.id.desc()).limit(100))
    return jsonify([n.public() for n in rows])


@api.post('/notifications/read')
@login_required
def mark_read():
    db.session.execute(db.update(Notification).where(Notification.user_id == current_user.id).values(read=True))
    db.session.commit()
    return jsonify(ok=True)


@api.get('/articles')
@login_required
def articles():
    return jsonify([a.public() for a in db.session.scalars(db.select(Article).order_by(Article.updated_at.desc()))])


@api.post('/articles')
@roles('admin', 'agent')
def create_article():
    body = data()
    article = Article(title=string(body, 'title', 5, 180), category=choice(body, 'category', CATEGORIES), body=string(body, 'body', 20, 20000))
    db.session.add(article)
    db.session.commit()
    return jsonify(article.public()), 201


@api.patch('/articles/<int:aid>')
@roles('admin', 'agent')
def update_article(aid):
    article = db.get_or_404(Article, aid)
    body = data()
    article.title = string(body, 'title', 5, 180)
    article.category = choice(body, 'category', CATEGORIES)
    article.body = string(body, 'body', 20, 20000)
    article.updated_at = now()
    db.session.commit()
    return jsonify(article.public())
