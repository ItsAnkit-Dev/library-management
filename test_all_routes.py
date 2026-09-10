from app import create_app
from models import db, User, Role

app = create_app('testing')

def test_all_routes():
    with app.test_client() as client:
        with app.app_context():
            # Setup users
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', email='admin@a.com', full_name='Admin', role=Role.SUPER_ADMIN)
                admin.set_password('123456')
                db.session.add(admin)
                
            student = User.query.filter_by(username='student').first()
            if not student:
                student = User(username='student', email='student@a.com', full_name='Student', role=Role.STUDENT)
                student.set_password('123456')
                db.session.add(student)
                
            lib = User.query.filter_by(username='lib').first()
            if not lib:
                lib = User(username='lib', email='lib@a.com', full_name='Lib', role=Role.LIBRARIAN)
                lib.set_password('123456')
                db.session.add(lib)
                
            db.session.commit()
            
            # Map of roles to endpoints they should access
            endpoints = [
                # Admin
                ('/admin/dashboard', 'admin'),
                ('/admin/books', 'admin'),
                ('/admin/books/add', 'admin'),
                ('/admin/categories', 'admin'),
                ('/admin/issues', 'admin'),
                ('/admin/members', 'admin'),
                ('/admin/members/add', 'admin'),
                ('/admin/settings', 'admin'),
                ('/admin/fines', 'admin'),
                ('/admin/reports', 'admin'),
                ('/admin/activity-log', 'admin'),
                
                # Librarian
                ('/librarian/dashboard', 'lib'),
                ('/librarian/issue', 'lib'),
                ('/librarian/return', 'lib'),
                ('/librarian/issues', 'lib'),
                
                # Student
                ('/student/dashboard', 'student'),
                ('/student/my-books', 'student'),
                ('/student/history', 'student'),
                ('/student/browse', 'student'),
                ('/student/recommendations', 'student'),
                ('/student/wishlist', 'student'),
                ('/student/notifications', 'student'),
            ]
            
            for url, role in endpoints:
                user = locals()[role]
                with app.test_client() as new_client:
                    new_client.post('/login', data={'login': user.username, 'password': '123456'})
                    resp = new_client.get(url)
                    if resp.status_code not in (200, 302):
                        print(f"Error on {url} (Role: {role}) - Status: {resp.status_code}")
                        print(resp.text[:500])
                        return
            print("All routes rendered successfully!")

if __name__ == "__main__":
    test_all_routes()
