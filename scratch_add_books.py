import os
import urllib.request
from app import create_app
from models import db, Book, Category

def download_placeholder():
    cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
    os.makedirs(cover_dir, exist_ok=True)
    target_path = os.path.join(cover_dir, 'default_cover.png')
    
    url = "https://via.placeholder.com/300x450/6366f1/ffffff?text=Book+Cover"
    try:
        urllib.request.urlretrieve(url, target_path)
        print(f"Placeholder image downloaded to {target_path}")
    except Exception as e:
        print(f"Failed to download placeholder: {e}")

def add_bca_books():
    app = create_app('development')
    with app.app_context():
        # Ensure 'Computer Science' category exists
        cat_name = "Computer Science"
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            category = Category(name=cat_name, description="Books related to Computer Science, Programming, and BCA.", color="#10b981", icon="fa-laptop-code")
            db.session.add(category)
            db.session.commit()
            print("Category 'Computer Science' created.")
            
        bca_books = [
            {"title": "Let Us C", "author": "Yashavant Kanetkar", "isbn": "9788183331630", "pub_year": 2017, "description": "A comprehensive guide to C Programming.", "total_copies": 5},
            {"title": "The C++ Programming Language", "author": "Bjarne Stroustrup", "isbn": "9780321563842", "pub_year": 2013, "description": "The definitive guide to C++ by its creator.", "total_copies": 3},
            {"title": "Java: The Complete Reference", "author": "Herbert Schildt", "isbn": "9781260440232", "pub_year": 2018, "description": "Comprehensive guide covering the entire Java programming language.", "total_copies": 4},
            {"title": "Python Crash Course", "author": "Eric Matthes", "isbn": "9781593279288", "pub_year": 2019, "description": "A hands-on, project-based introduction to programming with Python.", "total_copies": 6},
            {"title": "Data Structures and Algorithms in C++", "author": "Adam Drozdek", "isbn": "9781133608424", "pub_year": 2012, "description": "In-depth coverage of data structures and algorithms.", "total_copies": 3},
            {"title": "Database System Concepts", "author": "Abraham Silberschatz", "isbn": "9780078022159", "pub_year": 2019, "description": "Comprehensive textbook on database management systems (DBMS).", "total_copies": 5},
            {"title": "Computer Networking: A Top-Down Approach", "author": "James Kurose", "isbn": "9780133594140", "pub_year": 2016, "description": "Modern approach to computer networking.", "total_copies": 4},
            {"title": "Operating System Concepts", "author": "Abraham Silberschatz", "isbn": "9781119456339", "pub_year": 2018, "description": "The dinosaur book covering all operating system core concepts.", "total_copies": 4},
            {"title": "HTML and CSS: Design and Build Websites", "author": "Jon Duckett", "isbn": "9781118008188", "pub_year": 2011, "description": "A visual guide to web development.", "total_copies": 5},
            {"title": "JavaScript and JQuery", "author": "Jon Duckett", "isbn": "9781118531648", "pub_year": 2014, "description": "Interactive front-end web development guide.", "total_copies": 4},
            {"title": "Software Engineering: A Practitioner's Approach", "author": "Roger S. Pressman", "isbn": "9780078022128", "pub_year": 2014, "description": "Classic software engineering textbook.", "total_copies": 3},
            {"title": "Computer Fundamentals", "author": "P.K. Sinha", "isbn": "9788176567527", "pub_year": 2004, "description": "Introduction to computers and their functions.", "total_copies": 7},
            {"title": "Discrete Mathematics and Its Applications", "author": "Kenneth H. Rosen", "isbn": "9780073383095", "pub_year": 2011, "description": "Essential mathematics for computer science students.", "total_copies": 3},
            {"title": "Digital Design", "author": "M. Morris Mano", "isbn": "9780132774208", "pub_year": 2012, "description": "A clear, accessible introduction to digital design.", "total_copies": 2},
            {"title": "Object-Oriented Programming in C++", "author": "Robert Lafore", "isbn": "9780672323089", "pub_year": 2001, "description": "Fundamental concepts of OOP using C++.", "total_copies": 4},
            {"title": "Cloud Computing: Concepts, Technology & Architecture", "author": "Thomas Erl", "isbn": "9780133387520", "pub_year": 2013, "description": "Definitive guide to cloud computing technologies.", "total_copies": 2},
            {"title": "Cyber Security", "author": "Nina Godbole", "isbn": "9788126521791", "pub_year": 2014, "description": "Comprehensive introduction to cyber security threats and defense.", "total_copies": 3},
        ]
        
        added_count = 0
        for b in bca_books:
            # Check if book already exists
            existing = Book.query.filter_by(isbn=b['isbn']).first()
            if not existing:
                new_book = Book(
                    title=b['title'],
                    author=b['author'],
                    isbn=b['isbn'],
                    pub_year=b['pub_year'],
                    description=b['description'],
                    category_id=category.id,
                    total_copies=b['total_copies'],
                    available_copies=b['total_copies'],
                    cover_image='default_cover.png'
                )
                db.session.add(new_book)
                added_count += 1
        
        db.session.commit()
        print(f"Successfully added {added_count} new BCA books.")

if __name__ == '__main__':
    download_placeholder()
    add_bca_books()
