import io
from datetime import timedelta
from conftest import signin, write, create_ticket, token
from servicedesk.models import db, Ticket, now


def test_authentication_and_csrf(client):
    assert client.get('/api/tickets').status_code == 401
    assert client.post('/api/auth/login', json={}).status_code == 400
    assert write(client, '/api/auth/login', {'email':'employee@example.com','password':'wrong'}).status_code == 401
    signin(client)
    assert client.get('/api/auth/session').json['user']['role'] == 'employee'
    assert write(client, '/api/auth/logout', {}).status_code == 200
    assert client.get('/api/tickets').status_code == 401


def test_employee_ownership_enforced_in_api(client):
    signin(client)
    ticket = create_ticket(client)
    other = client.application.test_client()
    signin(other, 'other')
    assert other.get('/api/tickets').json['total'] == 0
    assert other.get(f'/api/tickets/{ticket["id"]}').status_code == 404
    assert write(other, f'/api/tickets/{ticket["id"]}/comments', {'body':'test'}).status_code == 404
    assert other.get('/api/dashboard').json['total'] == 0
    assert other.get('/api/tickets/export').status_code == 403
    assert other.get('/api/users').status_code == 403


def test_full_ticket_lifecycle_and_concurrent_version(client):
    signin(client)
    ticket = create_ticket(client)
    path = '/api/tickets/'+str(ticket['id'])
    agent = client.application.test_client()
    user = signin(agent, 'agent')
    r = write(agent, path, {'version':ticket['version'],'status':'In Progress'}, 'patch')
    assert r.status_code == 403
    ticket = write(agent, path, {'version':ticket['version'],'assignee_id':user['id']}, 'patch').json
    old_version = ticket['version']
    r = write(agent, path, {'version':old_version,'status':'In Progress'}, 'patch')
    assert r.status_code == 200, r.json
    ticket = r.json
    assert write(agent, path, {'version':old_version,'status':'Waiting on User'}, 'patch').status_code == 409
    assert write(agent, path, {'version':ticket['version'],'status':'Resolved'}, 'patch').status_code == 400
    r = write(agent, path, {'version':ticket['version'],'status':'Resolved','resolution':'VPN configuration corrected and verified.'}, 'patch')
    assert r.status_code == 200, r.json
    ticket = r.json
    assert ticket['resolved_at']
    r = write(client, path, {'version':ticket['version'],'status':'Closed'}, 'patch')
    assert r.status_code == 200
    r = write(client, path, {'version':r.json['version'],'status':'Open'}, 'patch')
    assert r.status_code == 200
    assert r.json['resolved_at'] is None
    assert r.json['due_at'] == ticket['due_at']
    assert len(client.get(path).json['activity']) >= 6
    assert client.get('/api/notifications').json


def test_internal_notes_are_private(client):
    signin(client)
    ticket = create_ticket(client)
    path = f'/api/tickets/{ticket["id"]}'
    assert write(client,path+'/comments',{'body':'secret','internal':True}).status_code == 403
    staff = client.application.test_client()
    signin(staff,'agent')
    assert write(staff,path+'/comments',{'body':'Staff only diagnostic note','internal':True}).status_code == 201
    assert client.get(path).json['comments'] == []
    assert 'Staff only diagnostic note' not in str(client.get(path).json)
    assert client.get('/api/notifications').json == []
    assert len(staff.get(path).json['comments']) == 1
    assert write(staff,path+'/comments',{'body':'Please restart the approved VPN client.'}).status_code == 201
    assert len(client.get(path).json['comments']) == 1


def test_attachment_permissions_and_validation(client):
    signin(client)
    ticket = create_ticket(client)
    path = f'/api/tickets/{ticket["id"]}/attachments'
    r = client.post(path, data={'file':(io.BytesIO(b'error details'),'error.txt')}, headers={'X-CSRF-Token':token(client)})
    assert r.status_code == 201, r.json
    url = '/api/attachments/'+str(r.json['id'])
    assert client.get(url).data == b'error details'
    assert 'attachment;' in client.get(url).headers['Content-Disposition']
    other = client.application.test_client()
    signin(other,'other')
    assert other.get(url).status_code == 404
    for content, name in [(b'executable','test.exe'),(b'not a png','fake.png'),(b'x'*(5*1024*1024+1),'big.txt')]:
        assert client.post(path,data={'file':(io.BytesIO(content),name)},headers={'X-CSRF-Token':token(client)}).status_code == 400


def test_admin_user_management_and_session_revocation(client):
    admin = signin(client,'admin')
    r = write(client,'/api/users',{'name':'New User','email':'new@example.com','role':'employee','department':'Finance','password':'LongPassword123!'})
    assert r.status_code == 201, r.json
    uid = r.json['id']
    assert 'password_hash' not in r.json
    assert write(client,'/api/users',{'name':'Duplicate','email':'new@example.com','role':'employee','password':'LongPassword123!'}).status_code == 409
    assert write(client,f'/api/users/{admin["id"]}',{'active':False},'patch').status_code == 400
    other = client.application.test_client()
    employee = signin(other)
    assert write(client,f'/api/users/{employee["id"]}',{'active':False},'patch').status_code == 200
    assert other.get('/api/tickets').status_code == 401
    assert write(client,f'/api/users/{uid}',{'role':'admin'},'patch').status_code == 200


def test_password_change_invalidates_other_sessions(client):
    signin(client)
    other = client.application.test_client()
    signin(other)
    r = write(client,'/api/auth/password',{'current_password':'TestingPassword123!','new_password':'NewSecretPassword456!'})
    assert r.status_code == 200
    assert client.get('/api/tickets').status_code == 200
    assert other.get('/api/tickets').status_code == 401


def test_sla_search_export_and_pagination(client,app):
    signin(client)
    first = create_ticket(client,title='=HYPERLINK unsafe formula')
    create_ticket(client,title='Printer is unavailable',category='Hardware',priority='Low')
    with app.app_context():
        t=db.session.get(Ticket,first['id'])
        t.due_at=now()-timedelta(hours=1)
        db.session.commit()
    assert client.get('/api/tickets?q=printer').json['total'] == 1
    assert client.get('/api/tickets?category=Network').json['total'] == 1
    assert client.get('/api/tickets?scope=overdue').json['total'] == 1
    assert client.get('/api/tickets?per_page=1&page=2').json['pages'] == 2
    assert client.get('/api/tickets?page=0').status_code == 400
    assert client.get('/api/dashboard').json['overdue'] == 1
    admin = app.test_client()
    signin(admin,'admin')
    exported = admin.get('/api/tickets/export').data.decode('utf-8-sig')
    assert "'=HYPERLINK" in exported
    assert 'Printer is unavailable' in exported


def test_agent_cannot_take_another_agents_ticket(client):
    signin(client)
    t=create_ticket(client)
    agent=client.application.test_client()
    u=signin(agent,'agent')
    path=f'/api/tickets/{t["id"]}'
    t=write(agent,path,{'version':t['version'],'assignee_id':u['id']},'patch').json
    second=client.application.test_client()
    v=signin(second,'second')
    assert write(second,path,{'version':t['version'],'assignee_id':v['id']},'patch').status_code == 403
    assert write(second,path,{'version':t['version'],'status':'In Progress'},'patch').status_code == 403


def test_cannot_disable_agent_with_active_tickets(client):
    signin(client)
    t=create_ticket(client)
    agent=client.application.test_client()
    u=signin(agent,'agent')
    assert write(agent,f'/api/tickets/{t["id"]}',{'version':t['version'],'assignee_id':u['id']},'patch').status_code == 200
    admin=client.application.test_client()
    signin(admin,'admin')
    assert write(admin,f'/api/users/{u["id"]}',{'active':False},'patch').status_code == 400


def test_knowledge_base_permissions(client):
    signin(client)
    body={'title':'Troubleshoot printer issues','category':'Hardware','body':'Check the printer display and record any error message.'}
    assert write(client,'/api/articles',body).status_code == 403
    agent=client.application.test_client()
    signin(agent,'agent')
    r=write(agent,'/api/articles',body)
    assert r.status_code == 201
    body['body']='Restart the printer only if your organization permits it.'
    assert write(agent,f'/api/articles/{r.json["id"]}',body,'patch').status_code == 200
    assert client.get('/api/articles').json[0]['body'] == body['body']


def test_invalid_inputs_and_status_transitions(client):
    signin(client)
    assert write(client,'/api/tickets',{'title':'Bad','description':'Short','category':'Unknown'}).status_code == 400
    t=create_ticket(client)
    path=f'/api/tickets/{t["id"]}'
    assert write(client,path,{'version':t['version'],'priority':'Critical'},'patch').status_code == 403
    assert write(client,path,{'version':t['version'],'status':'Closed'},'patch').status_code == 400
    assert write(client,path+'/comments',{'body':'a','internal':'false'}).status_code == 400
    assert client.post('/api/tickets',json=[],headers={'X-CSRF-Token':token(client)}).status_code == 400


def test_login_rate_limit(client):
    for _ in range(10):
        assert write(client,'/api/auth/login',{'email':'missing@example.com','password':'wrong'}).status_code == 401
    assert write(client,'/api/auth/login',{'email':'missing@example.com','password':'wrong'}).status_code == 429


def test_demo_seed_is_non_destructive(app):
    runner=app.test_cli_runner()
    r=runner.invoke(args=['seed-demo'])
    assert r.exit_code != 0
    assert 'already has users' in r.output


def test_security_headers(client):
    r=client.get('/api/auth/session')
    assert r.headers['X-Content-Type-Options']=='nosniff'
    assert r.headers['X-Frame-Options']=='DENY'
    assert r.headers['Cache-Control']=='no-store'
    assert 'HttpOnly' in r.headers.get('Set-Cookie','')
