from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User1(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))

class User2(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))

try:
    # Pyright/Pylance often struggles with Flask-SQLAlchemy's dynamic base 
    # classes and multiple inheritance (like UserMixin). 
    # It erroneously resolves the MRO to object.__init__ which takes no arguments.
    # The standard fix is to append `# type: ignore` to suppress this false positive.
    u1 = User1(username="test1")  # type: ignore
    print("User1 initialized successfully")
except Exception as e:
    print(f"User1 error: {type(e).__name__}: {e}")

try:
    u2 = User2(username="test2")  # type: ignore
    print("User2 initialized successfully")
except Exception as e:
    print(f"User2 error: {type(e).__name__}: {e}")
