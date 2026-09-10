import os
import urllib.request
import urllib.parse
import json
import time
from app import create_app
from models import db, Book

def fetch_openlibrary_search_cover(title, author):
    query = f"title={urllib.parse.quote(title)}&author={urllib.parse.quote(author)}"
    url = f"https://openlibrary.org/search.json?{query}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if 'docs' in data and len(data['docs']) > 0:
                for doc in data['docs']:
                    if 'cover_i' in doc:
                        cover_id = doc['cover_i']
                        return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    except Exception as e:
        print(f"  OpenLibrary Search failed for {title}: {e}")
    return None

def retry_missing_covers():
    app = create_app('development')
    with app.app_context():
        cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
        
        books = Book.query.filter_by(cover_image='default_cover.png').all()
        for b in books:
            print(f"Retrying with OpenLibrary Search: {b.title}...")
            cover_url = fetch_openlibrary_search_cover(b.title, b.author)
            if cover_url:
                filename = f"cover_{b.isbn}.jpg"
                filepath = os.path.join(cover_dir, filename)
                try:
                    urllib.request.urlretrieve(cover_url, filepath)
                    b.cover_image = filename
                    db.session.commit()
                    print(f"  Successfully downloaded real cover for {b.title}")
                except Exception as e:
                    print(f"  Failed to save cover: {e}")
            else:
                print(f"  Still no cover found for {b.title}")
            time.sleep(1)

if __name__ == '__main__':
    retry_missing_covers()
