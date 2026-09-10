from app import create_app
from models import db, Book, Category

def add_more_bca_books():
    app = create_app('development')
    with app.app_context():
        category = Category.query.filter_by(name="Computer Science").first()
        if not category:
            category = Category(name="Computer Science", description="Books related to Computer Science, Programming, and BCA.", color="#10b981", icon="fa-laptop-code")
            db.session.add(category)
            db.session.commit()
            
        more_books = [
            {"title": "Programming in ANSI C", "author": "E Balagurusamy", "isbn": "9789339219666", "pub_year": 2012, "description": "A comprehensive book on C programming by E Balagurusamy.", "total_copies": 6},
            {"title": "Data Structures Using C", "author": "Reema Thareja", "isbn": "9780198099307", "pub_year": 2014, "description": "Detailed explanation of data structures using C language.", "total_copies": 5},
            {"title": "Introduction to Algorithms", "author": "Thomas H. Cormen", "isbn": "9780262033848", "pub_year": 2009, "description": "The standard textbook on algorithms.", "total_copies": 4},
            {"title": "Head First Java", "author": "Kathy Sierra", "isbn": "9780596009205", "pub_year": 2005, "description": "A brain-friendly guide to Java.", "total_copies": 7},
            {"title": "Introduction to Automata Theory", "author": "John E. Hopcroft", "isbn": "9780201441246", "pub_year": 2001, "description": "Classic text on automata theory and computation.", "total_copies": 2},
            {"title": "Computer Organization and Architecture", "author": "William Stallings", "isbn": "9780134101613", "pub_year": 2015, "description": "Designing for performance.", "total_copies": 3},
        ]
        
        added = 0
        for b in more_books:
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
                added += 1
                
        db.session.commit()
        print(f"Added {added} more books.")

if __name__ == '__main__':
    add_more_bca_books()
