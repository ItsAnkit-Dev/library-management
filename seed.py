from app import create_app
from models import db, User, Role, Category, Book, SystemSettings
import random

def seed_database():
    app = create_app("development")
    
    with app.app_context():
        # Clean existing (optional, but good for a fresh start)
        db.drop_all()
        db.create_all()

        print("Creating users...")
        # Super Admin
        admin = User(
            username="admin", email="admin@library.com",
            full_name="System Admin", role=Role.SUPER_ADMIN,
            is_active=True
        )
        admin.set_password("admin123")
        
        # Librarians
        lib1 = User(
            username="lib1", email="librarian1@library.com",
            full_name="Sarah Connor", role=Role.LIBRARIAN,
            phone="1234567890", is_active=True
        )
        lib1.set_password("lib123")
        
        lib2 = User(
            username="lib2", email="librarian2@library.com",
            full_name="John Wick", role=Role.LIBRARIAN,
            phone="0987654321", is_active=True
        )
        lib2.set_password("lib123")

        # Students
        students = []
        for i in range(1, 9):
            stu = User(
                username=f"student{i}", email=f"student{i}@university.edu",
                full_name=f"Student Name {i}", role=Role.STUDENT,
                student_id=f"STU202400{i}", membership_id=f"MEM202400{i}",
                course="Computer Science", department="Engineering",
                is_active=True
            )
            stu.set_password("student123")
            students.append(stu)
            
        db.session.add_all([admin, lib1, lib2] + students)
        db.session.commit()

        print("Creating categories...")
        categories = [
            Category(name="Programming", color="#ff0000", icon="fa-code"),
            Category(name="Data Science", color="#00ff00", icon="fa-database"),
            Category(name="Fiction", color="#0000ff", icon="fa-magic"),
            Category(name="Science", color="#ff00ff", icon="fa-flask"),
            Category(name="History", color="#ffff00", icon="fa-monument"),
        ]
        db.session.add_all(categories)
        db.session.commit()

        print("Creating books...")
        books_data = [
            ("Clean Code", "Robert C. Martin", "9780132350884", 1),
            ("The Pragmatic Programmer", "Andy Hunt", "9780135957059", 1),
            ("Design Patterns", "Erich Gamma", "9780201633610", 1),
            ("Python Crash Course", "Eric Matthes", "9781593279288", 1),
            ("Deep Learning", "Ian Goodfellow", "9780262035613", 2),
            ("Data Science for Business", "Foster Provost", "9781449361327", 2),
            ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", 3),
            ("1984", "George Orwell", "9780451524935", 3),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", 4),
            ("Sapiens", "Yuval Noah Harari", "9780062316097", 5),
            ("Dune", "Frank Herbert", "9780441172719", 3),
            ("The Hobbit", "J.R.R. Tolkien", "9780547928227", 3),
            ("Introduction to Algorithms", "Thomas H. Cormen", "9780262033848", 1),
            ("Head First Design Patterns", "Eric Freeman", "9780596007126", 1),
            ("Clean Architecture", "Robert C. Martin", "9780134494166", 1),
            ("Machine Learning Yearning", "Andrew Ng", "9780132350899", 2),
            ("Thinking, Fast and Slow", "Daniel Kahneman", "9780374533557", 5),
            ("Cosmos", "Carl Sagan", "9780345331359", 4),
            ("The Martian", "Andy Weir", "9780804139021", 3),
            ("To Kill a Mockingbird", "Harper Lee", "9780060935467", 3),
            ("Fahrenheit 451", "Ray Bradbury", "9781451673319", 3),
            ("Guns, Germs, and Steel", "Jared Diamond", "9780393317558", 5),
        ]

        books = []
        for b in books_data:
            copies = random.randint(1, 5)
            book = Book(
                title=b[0], author=b[1], isbn=b[2], category_id=b[3],
                total_copies=copies, available_copies=copies,
                publisher="Tech Press" if b[3] in [1,2] else "Penguin",
                pub_year=random.randint(1990, 2023),
                added_by_id=admin.id
            )
            books.append(book)
            
        db.session.add_all(books)
        db.session.commit()

        print("Setting default settings...")
        SystemSettings.set("library_name", "Modern Library")
        SystemSettings.set("library_tagline", "Knowledge is Power")
        SystemSettings.set("fine_per_day", 2.0)
        SystemSettings.set("max_fine_limit", 200.0)
        SystemSettings.set("max_books_student", 3)
        SystemSettings.set("default_issue_days", 14)
        
        print("Database seeded successfully!")
        print("--------------------------------------------------")
        print("Admin Login: admin / admin123")
        print("Librarian Login: lib1 / lib123")
        print("Student Login: student1 / student123")
        print("--------------------------------------------------")

if __name__ == "__main__":
    seed_database()
