from app import create_app
from models import db, User, Role

app = create_app('testing')

with app.test_client() as client:
    with app.app_context():
        # Ensure there is a user
        u = User.query.first()
        if not u:
            u = User(username='test', email='test@test.com', full_name='Test', role=Role.STUDENT)
            u.set_password('123456')
            db.session.add(u)
            db.session.commit()
            
        print("User:", u)
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.id)
            sess['_fresh'] = True
            
        # Hit dashboard
        resp = client.get('/student/dashboard')
        print("Dashboard status:", resp.status_code)
        if resp.status_code != 200:
            print("Error in dashboard:", resp.text)
            
        # Check admin members
        u.role = Role.SUPER_ADMIN
        db.session.commit()
        resp = client.get('/admin/members/add')
        print("Admin member_form add status:", resp.status_code)
        if resp.status_code != 200:
            print("Error in member_form:", resp.text)
