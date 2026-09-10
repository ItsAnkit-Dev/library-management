import os
import urllib.request
import urllib.parse
import json
from app import create_app
from models import db, Book

def fetch(title, author):
    # Trying different queries: just title, or title + author
    queries = [
        f'intitle:"{title}" inauthor:"{author}"',
        f'intitle:"{title}"'
    ]
    for query in queries:
        url = 'https://www.googleapis.com/books/v1/volumes?q=' + urllib.parse.quote(query)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if 'items' in data and len(data['items']) > 0:
                    for item in data['items']:
                        image_links = item.get('volumeInfo', {}).get('imageLinks', {})
                        img_url = image_links.get('thumbnail') or image_links.get('smallThumbnail')
                        if img_url:
                            return img_url.replace('http:', 'https:').replace('&edge=curl', '')
        except Exception as e:
            print(f'Error for query {query}: {e}')
    return None

app = create_app('development')
with app.app_context():
    cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
    books = Book.query.filter_by(cover_image='default_cover.png').all()
    for b in books:
        print(f"Fetching cover for {b.title}...")
        url = fetch(b.title, b.author)
        if url:
            filename = f'cover_{b.isbn}.jpg'
            try:
                urllib.request.urlretrieve(url, os.path.join(cover_dir, filename))
                b.cover_image = filename
                db.session.commit()
                print(f'Fixed {b.title}')
            except Exception as e:
                print(f"Failed to save image: {e}")
        else:
            print(f'Failed {b.title}')
