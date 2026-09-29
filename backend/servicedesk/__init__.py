"""Application factory, session authentication, CSRF and error handling."""
import os
import secrets
from datetime import timedelta
from pathlib import Path
from flask import Flask, jsonify, request, session, send_from_directory
from flask_login import LoginManager
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.exceptions import HTTPException
from .models import db, User

login = LoginManager()


def create_app(test_config=None):
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / '.env')
    app = Flask(__name__, static_folder=None, instance_path=str(root / 'instance'))
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret = os.getenv('SECRET_KEY')
    if not secret:
        secret_file = Path(app.instance_path) / 'session.key'
        if not secret_file.exists():
            try:
                with secret_file.open('x') as f:
                    f.write(secrets.token_hex(32))
                secret_file.chmod(0o600)
            except FileExistsError:
                pass
        secret = secret_file.read_text().strip()
    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///servicedesk.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True},
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / 'uploads'),
        FRONTEND_DIR=str(root.parent / 'frontend' / 'dist'),
        CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login.init_app(app)

    @login.user_loader
    def load_user(value):
        try:
            uid, version = value.split(':')
            user = db.session.get(User, int(uid))
            return user if user and user.active and user.session_version == int(version) else None
        except (ValueError, TypeError):
            return None

    @login.unauthorized_handler
    def unauthorized():
        return jsonify(error='Please sign in to continue.'), 401

    @app.before_request
    def csrf_check():
        if request.path.startswith('/api/') and request.method in ('POST', 'PATCH', 'PUT', 'DELETE') and app.config['CSRF_ENABLED']:
            supplied = request.headers.get('X-CSRF-Token', '')
            expected = session.get('csrf', '')
            if not expected or not secrets.compare_digest(supplied, expected):
                return jsonify(error='Session expired. Refresh the page and try again.'), 400

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        return jsonify(error='This record conflicts with an existing record. Refresh and try again.'), 409

    @app.errorhandler(StaleDataError)
    def stale_error(error):
        db.session.rollback()
        return jsonify(error='Another user updated this ticket. Refresh before saving.'), 409

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        app.logger.exception('Request failed')
        return jsonify(error='The server could not complete the request.'), 500

    from .api import api
    app.register_blueprint(api, url_prefix='/api')
    from .commands import register_commands
    register_commands(app)

    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path=''):
        if path.startswith('api/'):
            return jsonify(error='Endpoint not found.'), 404
        directory = Path(app.config['FRONTEND_DIR'])
        if path and (directory / path).is_file() and (directory / path).resolve().is_relative_to(directory.resolve()):
            return send_from_directory(directory, path)
        if (directory / 'index.html').exists():
            return send_from_directory(directory, 'index.html')
        return 'Frontend not built. Run npm install and npm run build in frontend/.', 503

    return app
