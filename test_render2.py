from app import create_app
from models import db, User, Role

app = create_app('testing')

with app.test_client() as client:
    with app.app_context():
        u = User.query.filter_by(username='test_admin').first()
        if not u:
            u = User(username='test_admin', email='test_admin@test.com', full_name='Test Admin', role=Role.SUPER_ADMIN)
            u.set_password('123456')
            db.session.add(u)
            db.session.commit()
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.id)
            sess['_fresh'] = True
            
        resp = client.get('/admin/members/add')
        print("Add member status:", resp.status_code)
        if resp.status_code != 200:
            print("Error in add member:", resp.text)
