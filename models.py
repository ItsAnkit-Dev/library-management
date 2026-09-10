"""
SQLAlchemy models for the Library Management System.
Defines: User, Category, Book, BookCopy, Issue, Fine,
         Reservation, ActivityLog, SystemSettings
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations (stored as strings in SQLite)
# ─────────────────────────────────────────────────────────────────────────────

class Role:
    SUPER_ADMIN = "super_admin"
    LIBRARIAN   = "librarian"
    STUDENT     = "student"
    ALL = [SUPER_ADMIN, LIBRARIAN, STUDENT]

class BookStatus:
    AVAILABLE = "available"
    ISSUED    = "issued"
    LOST      = "lost"
    DAMAGED   = "damaged"

class IssueStatus:
    ISSUED    = "issued"
    RETURNED  = "returned"
    OVERDUE   = "overdue"
    LOST      = "lost"

class FineStatus:
    PENDING = "pending"
    PAID    = "paid"
    WAIVED  = "waived"

class ReservationStatus:
    PENDING   = "pending"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"

class ActivityType:
    LOGIN       = "login"
    LOGOUT      = "logout"
    BOOK_ADD    = "book_add"
    BOOK_EDIT   = "book_edit"
    BOOK_DELETE = "book_delete"
    ISSUE       = "issue"
    RETURN      = "return"
    RENEW       = "renew"
    FINE_PAY    = "fine_pay"
    FINE_WAIVE  = "fine_waive"
    MEMBER_ADD  = "member_add"
    MEMBER_EDIT = "member_edit"
    RESERVE     = "reserve"
    SETTINGS    = "settings"
    REVIEW      = "review"
    GOAL_SET    = "goal_set"
    FINE_ONLINE = "fine_online_pay"


class NotificationType:
    DUE_REMINDER  = "due_reminder"
    OVERDUE_ALERT = "overdue_alert"
    FINE_ALERT    = "fine_alert"
    NEW_BOOK      = "new_book"
    WISHLIST_AVAIL = "wishlist_avail"
    GENERAL       = "general"


# ─────────────────────────────────────────────────────────────────────────────
# User (Authentication + Role)
# ─────────────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String(80),  unique=True, nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    role           = db.Column(db.String(20),  nullable=False, default=Role.STUDENT)
    is_active      = db.Column(db.Boolean, default=True)

    # Profile
    full_name      = db.Column(db.String(120), nullable=False)
    phone          = db.Column(db.String(20))
    address        = db.Column(db.Text)
    profile_pic    = db.Column(db.String(200), default="default_avatar.png")

    # Student-specific
    student_id     = db.Column(db.String(50), unique=True, nullable=True)
    membership_id  = db.Column(db.String(50), unique=True, nullable=True)
    department     = db.Column(db.String(100))
    course         = db.Column(db.String(100))
    max_books      = db.Column(db.Integer, default=3)

    # Timestamps
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))
    last_login     = db.Column(db.DateTime)
    is_deleted     = db.Column(db.Boolean, default=False)

    # Relationships
    issues       = db.relationship("Issue",       back_populates="member",
                                   foreign_keys="Issue.member_id", lazy="dynamic")
    fines        = db.relationship("Fine",        back_populates="member",
                                   foreign_keys="Fine.member_id", lazy="dynamic")
    reservations = db.relationship("Reservation", back_populates="member", lazy="dynamic")
    activities   = db.relationship("ActivityLog", back_populates="user",   lazy="dynamic")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ── Password helpers ──────────────────────────────────────────────────────
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def is_admin(self):
        return self.role == Role.SUPER_ADMIN

    @property
    def is_librarian(self):
        return self.role == Role.LIBRARIAN

    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def active_issues_count(self):
        return self.issues.filter_by(status=IssueStatus.ISSUED).count()

    @property
    def total_pending_fine(self):
        total = db.session.query(db.func.sum(Fine.amount))\
                  .filter(Fine.member_id == self.id,
                          Fine.status == FineStatus.PENDING).scalar()
        return total or 0.0

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    color       = db.Column(db.String(7), default="#6366f1")   # hex colour for badge
    icon        = db.Column(db.String(50), default="fa-book")  # Font Awesome icon
    is_deleted  = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    books = db.relationship("Book", back_populates="category", lazy="dynamic")

    @property
    def active_book_count(self):
        return self.books.filter_by(is_deleted=False).count()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Category {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Book
# ─────────────────────────────────────────────────────────────────────────────

class Book(db.Model):
    __tablename__ = "books"

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    author        = db.Column(db.String(200), nullable=False)
    isbn          = db.Column(db.String(20),  unique=True, nullable=False)
    publisher     = db.Column(db.String(150))
    pub_year      = db.Column(db.Integer)
    edition       = db.Column(db.String(50))
    description   = db.Column(db.Text)
    language      = db.Column(db.String(50), default="English")
    pages         = db.Column(db.Integer)
    cover_image   = db.Column(db.String(200), default="default_cover.png")

    # Inventory
    total_copies     = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    status           = db.Column(db.String(20), default=BookStatus.AVAILABLE)

    # FK
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    # Timestamps / soft delete
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))
    is_deleted  = db.Column(db.Boolean, default=False)

    # Added-by
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    category     = db.relationship("Category",    back_populates="books")
    added_by     = db.relationship("User",        foreign_keys=[added_by_id])
    issues       = db.relationship("Issue",       back_populates="book", lazy="dynamic")
    reservations = db.relationship("Reservation", back_populates="book", lazy="dynamic")

    @property
    def is_available(self):
        return self.available_copies > 0 and not self.is_deleted

    @property
    def total_issued(self):
        return self.issues.filter_by(status=IssueStatus.ISSUED).count()

    @property
    def qr_filename(self):
        return f"qr_{self.isbn}.png"

    @property
    def cover_url(self):
        if self.cover_image and self.cover_image != 'default_cover.png':
            from flask import url_for
            return url_for('static', filename='uploads/covers/' + self.cover_image)
        import urllib.parse
        # Limit title length to prevent URL overflow, split words
        words = self.title.split()
        short_title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
        encoded_title = urllib.parse.quote_plus(short_title)
        return f"https://placehold.co/400x600/4F46E5/FFFFFF?text={encoded_title}"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Book '{self.title}' [{self.isbn}]>"


# ─────────────────────────────────────────────────────────────────────────────
# Issue (borrowing record)
# ─────────────────────────────────────────────────────────────────────────────

class Issue(db.Model):
    __tablename__ = "issues"

    id           = db.Column(db.Integer, primary_key=True)
    member_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book_id      = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    issued_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    issue_date   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    due_date     = db.Column(db.DateTime, nullable=False)
    return_date  = db.Column(db.DateTime, nullable=True)
    renewed_date = db.Column(db.DateTime, nullable=True)
    renew_count  = db.Column(db.Integer, default=0)

    status       = db.Column(db.String(20), default=IssueStatus.ISSUED)
    notes        = db.Column(db.Text)

    # Relationships
    member    = db.relationship("User", back_populates="issues", foreign_keys=[member_id])
    issued_by = db.relationship("User", foreign_keys=[issued_by_id])
    book      = db.relationship("Book", back_populates="issues")
    fine      = db.relationship("Fine", back_populates="issue",
                                uselist=False, cascade="all, delete-orphan")

    @property
    def is_overdue(self):
        if self.status == IssueStatus.ISSUED:
            return datetime.now(timezone.utc) > self.due_date.replace(tzinfo=timezone.utc)
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            delta = datetime.now(timezone.utc) - self.due_date.replace(tzinfo=timezone.utc)
            return delta.days
        return 0

    @property
    def days_until_due(self):
        now = datetime.now(timezone.utc)
        due = self.due_date.replace(tzinfo=timezone.utc)
        delta = (due - now).days
        return max(delta, 0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Issue book={self.book_id} member={self.member_id} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# Fine
# ─────────────────────────────────────────────────────────────────────────────

class Fine(db.Model):
    __tablename__ = "fines"

    id            = db.Column(db.Integer, primary_key=True)
    issue_id      = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=False)
    member_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount        = db.Column(db.Float, nullable=False, default=0.0)
    reason        = db.Column(db.String(200), default="Overdue")
    status        = db.Column(db.String(20), default=FineStatus.PENDING)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at       = db.Column(db.DateTime, nullable=True)
    paid_by_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    waived_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes         = db.Column(db.Text)

    # Relationships
    issue     = db.relationship("Issue", back_populates="fine")
    member    = db.relationship("User",  back_populates="fines", foreign_keys=[member_id])
    paid_by   = db.relationship("User",  foreign_keys=[paid_by_id])
    waived_by = db.relationship("User",  foreign_keys=[waived_by_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Fine ₹{self.amount} ({self.status})>"


# ─────────────────────────────────────────────────────────────────────────────
# Reservation (Wishlist)
# ─────────────────────────────────────────────────────────────────────────────

class Reservation(db.Model):
    __tablename__ = "reservations"

    id           = db.Column(db.Integer, primary_key=True)
    member_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book_id      = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    reserved_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    fulfilled_at = db.Column(db.DateTime, nullable=True)
    status       = db.Column(db.String(20), default=ReservationStatus.PENDING)
    notes        = db.Column(db.Text)

    member = db.relationship("User", back_populates="reservations",
                             foreign_keys=[member_id])
    book   = db.relationship("Book", back_populates="reservations",
                             foreign_keys=[book_id])

    __table_args__ = ()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Reservation book={self.book_id} member={self.member_id}>"

# ─────────────────────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────────────────────

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    activity     = db.Column(db.String(50), nullable=False)
    description  = db.Column(db.Text)
    ip_address   = db.Column(db.String(45))
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Optional reference to a book/issue
    book_id      = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=True)
    issue_id     = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=True)

    user = db.relationship("User", back_populates="activities")
    book = db.relationship("Book", foreign_keys=[book_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Log {self.activity} by user={self.user_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# System Settings (key-value store)
# ─────────────────────────────────────────────────────────────────────────────

class SystemSettings(db.Model):
    __tablename__ = "system_settings"

    id          = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(100), unique=True, nullable=False)
    value       = db.Column(db.Text)
    description = db.Column(db.String(200))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get(key: str, default=None):
        row = SystemSettings.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key: str, value, description: str = ""):
        row = SystemSettings.query.filter_by(key=key).first()
        if row:
            row.value = str(value)
            row.updated_at = datetime.now(timezone.utc)
        else:
            row = SystemSettings(key=key, value=str(value), description=description)  # type: ignore
            db.session.add(row)
        db.session.commit()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"


# ─────────────────────────────────────────────────────────────────────────────
# BookReview (ratings & reviews by students)
# ─────────────────────────────────────────────────────────────────────────────

class BookReview(db.Model):
    __tablename__ = "book_reviews"

    id         = db.Column(db.Integer, primary_key=True)
    book_id    = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)   # 1–5
    review     = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    book = db.relationship("Book", backref=db.backref("reviews", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("reviews", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("book_id", "user_id", name="uq_review_book_user"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Review book={self.book_id} user={self.user_id} rating={self.rating}>"


# ─────────────────────────────────────────────────────────────────────────────
# ReadingGoal (monthly book target for students)
# ─────────────────────────────────────────────────────────────────────────────

class ReadingGoal(db.Model):
    __tablename__ = "reading_goals"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    year       = db.Column(db.Integer, nullable=False)
    month      = db.Column(db.Integer, nullable=False)   # 1–12
    target     = db.Column(db.Integer, nullable=False, default=4)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("reading_goals", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "year", "month", name="uq_goal_user_month"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<ReadingGoal user={self.user_id} {self.year}-{self.month:02d} target={self.target}>"


# ─────────────────────────────────────────────────────────────────────────────
# Notification (in-app notification center)
# ─────────────────────────────────────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type       = db.Column(db.String(40), nullable=False, default="general")
    title      = db.Column(db.String(150), nullable=False)
    message    = db.Column(db.Text)
    is_read    = db.Column(db.Boolean, default=False)
    link       = db.Column(db.String(300))          # optional deep-link
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("notifications", lazy="dynamic"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Notification {self.type} user={self.user_id} read={self.is_read}>"
