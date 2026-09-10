import os
import urllib.request
import urllib.parse
import json
import time
from app import create_app
from models import db, Book, Category, Issue, Reservation

BOOKS_TO_ADD = [
    {"title": "The C Programming Language", "author": "Dennis Ritchie", "isbn": "9780131103627"},
    {"title": "Let Us C", "author": "Yashwant Kanetkar", "isbn": "9788183331630"},
    {"title": "Programming in ANSI C", "author": "E. Balagurusamy", "isbn": "9789339219666"},
    {"title": "Data Structures Using C", "author": "Reema Thareja", "isbn": "9780198099307"},
    {"title": "Java: The Complete Reference", "author": "Herbert Schildt", "isbn": "9781260440232"},
    {"title": "Head First Java", "author": "Kathy Sierra", "isbn": "9780596009205"},
    {"title": "Python Crash Course", "author": "Eric Matthes", "isbn": "9781593279288"},
    {"title": "Database System Concepts", "author": "Abraham Silberschatz", "isbn": "9780078022159"},
    {"title": "Computer Networks", "author": "Andrew S. Tanenbaum", "isbn": "9780132126953"},
    {"title": "Operating System Concepts", "author": "Abraham Silberschatz", "isbn": "9781118063330"},
    {"title": "Computer Fundamentals", "author": "P.K. Sinha", "isbn": "9788176567527"},
    {"title": "Digital Design", "author": "M. Morris Mano", "isbn": "9780132774208"},  # Replaced Digital Electronics with Digital Design by Morris Mano
    {"title": "Object Oriented Programming with C++", "author": "E. Balagurusamy", "isbn": "9781259029936"},
    {"title": "Web Technologies", "author": "Uttam K. Roy", "isbn": "9780198066224"},
    {"title": "Software Engineering", "author": "Ian Sommerville", "isbn": "9780133943030"},
    {"title": "Computer Organization and Architecture", "author": "William Stallings", "isbn": "9780134101613"},
    {"title": "Cloud Computing", "author": "Thomas Erl", "isbn": "9780133387520"},
    {"title": "Cyber Security", "author": "Nina Godbole", "isbn": "9788126521791"},
    {"title": "Discrete Mathematics and Its Applications", "author": "Kenneth H. Rosen", "isbn": "9780073383095"},
    {"title": "Artificial Intelligence", "author": "Elaine Rich", "isbn": "9780070087705"},
]

def fetch_google_books_cover(title, author):
    query = f"intitle:{title} inauthor:{author}"
    url = "https://www.googleapis.com/books/v1/volumes?q=" + urllib.parse.quote(query)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if 'items' in data and len(data['items']) > 0:
                volume_info = data['items'][0].get('volumeInfo', {})
                image_links = volume_info.get('imageLinks', {})
                # Try to get highest quality available thumbnail
                img_url = image_links.get('thumbnail') or image_links.get('smallThumbnail')
                if img_url:
                    # Upgrade http to https and remove zoom to get better quality if possible
                    img_url = img_url.replace('http:', 'https:').replace('&edge=curl', '')
                    return img_url
    except Exception as e:
        print(f"  Google API failed for {title}: {e}")
    return None

def fetch_openlibrary_cover(isbn):
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

def run_seed():
    app = create_app('development')
    with app.app_context():
        # Get or create category
        cat_name = "BCA Core Subjects"
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            category = Category(name=cat_name, description="Core subjects for BCA course.", color="#0ea5e9", icon="fa-laptop-code")
            db.session.add(category)
            db.session.commit()
            
        cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
        os.makedirs(cover_dir, exist_ok=True)
        
        # We will delete ALL existing books in the db to give a clean slate as requested (only BCA books)
        # First, delete dependent records
        Issue.query.delete()
        Reservation.query.delete()
        db.session.commit()
        Book.query.delete()
        db.session.commit()
        
        for b in BOOKS_TO_ADD:
            print(f"Processing: {b['title']}...")
            cover_url = fetch_google_books_cover(b['title'], b['author'])
            
            filename = f"cover_{b['isbn']}.jpg"
            filepath = os.path.join(cover_dir, filename)
            
            downloaded = False
            if cover_url:
                try:
                    urllib.request.urlretrieve(cover_url, filepath)
                    downloaded = True
                    print(f"  Downloaded from Google Books")
                except:
                    pass
            
            if not downloaded:
                try:
                    ol_url = fetch_openlibrary_cover(b['isbn'])
                    urllib.request.urlretrieve(ol_url, filepath)
                    # Open Library returns a 1x1 image if not found, we will check size
                    if os.path.getsize(filepath) > 1000:
                        downloaded = True
                        print(f"  Downloaded from OpenLibrary")
                    else:
                        os.remove(filepath)
                except:
                    pass
            
            if not downloaded:
                print(f"  Warning: No cover found for {b['title']}")
                filename = 'default_cover.png'
                
            new_book = Book(
                title=b['title'],
                author=b['author'],
                isbn=b['isbn'],
                pub_year=2020,
                description=f"A standard textbook: {b['title']} by {b['author']}.",
                category_id=category.id,
                total_copies=5,
                available_copies=5,
                cover_image=filename
            )
            db.session.add(new_book)
            time.sleep(0.5) # rate limit prevention
            
        db.session.commit()
        print("Successfully added 20 BCA books with realistic covers.")

if __name__ == '__main__':
    run_seed()
