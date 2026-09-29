import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servicedesk import create_app
from servicedesk.models import db, User


@pytest.fixture()
def app(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                      'SECRET_KEY': 'test-secret-only', 'UPLOAD_FOLDER': str(tmp_path / 'uploads')})
    with app.app_context():
        db.create_all()
        for name, role in [('Admin','admin'),('Agent','agent'),('Employee','employee'),('Other','employee'),('Second','agent')]:
            user = User(name=name, email=name.lower()+'@example.com', role=role)
            user.set_password('TestingPassword123!')
            db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def token(client):
    return client.get('/api/auth/session').json['csrf']


def write(client, url, body, method='post'):
    return getattr(client, method)(url, json=body, headers={'X-CSRF-Token': token(client)})


def signin(client, name='employee'):
    response = write(client, '/api/auth/login', {'email':name+'@example.com','password':'TestingPassword123!'})
    assert response.status_code == 200, response.json
    return response.json['user']


def create_ticket(client, **overrides):
    body = {'title':'Cannot connect to office VPN','description':'VPN connection fails with an error after signing in.', 'category':'Network','priority':'High'}
    body.update(overrides)
    response = write(client, '/api/tickets', body)
    assert response.status_code == 201, response.json
    return response.json
