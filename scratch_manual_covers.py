import os
import urllib.request
from app import create_app
from models import db, Book

MANUAL_COVERS = {
    "Programming in ANSI C": "https://images-na.ssl-images-amazon.com/images/P/0074604015.01.LZZZZZZZ.jpg",
    "Web Technologies": "https://slogix.in/images/web-technology/web-technologies.jpg"
}

app = create_app('development')
with app.app_context():
    cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
    os.makedirs(cover_dir, exist_ok=True)
    
    for title, url in MANUAL_COVERS.items():
        book = Book.query.filter_by(title=title).first()
        if book:
            filename = f"cover_{book.isbn}.jpg"
            filepath = os.path.join(cover_dir, filename)
            try:
                # Need custom User-Agent because some sites block python-urllib
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    with open(filepath, 'wb') as f:
                        f.write(response.read())
                book.cover_image = filename
                db.session.commit()
                print(f"Manually downloaded and fixed cover for: {title}")
            except Exception as e:
                print(f"Failed to manually download {title}: {e}")
