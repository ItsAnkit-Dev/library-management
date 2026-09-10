"""
API Blueprint – AJAX endpoints for live search, chart data, notifications.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from models import (
    db, Book, User, Issue, Fine, Category,
    FineStatus, Role
)

api_bp = Blueprint("api", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Book search (live / typeahead)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/books/search")
@login_required
def search_books():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    books = Book.query.filter(
        Book.is_deleted.is_(False),
        db.or_(
            Book.title.ilike(f"%{q}%"),
            Book.author.ilike(f"%{q}%"),
            Book.isbn.ilike(f"%{q}%"),
        )
    ).limit(10).all()

    return jsonify([{
        "id":      b.id,
        "title":   b.title,
        "author":  b.author,
        "isbn":    b.isbn,
        "available": b.available_copies,
        "status":  b.status,
    } for b in books])


# ─────────────────────────────────────────────────────────────────────────────
# Member search (live / typeahead)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/members/search")
@login_required
def search_members():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    members = User.query.filter(
        User.is_deleted.is_(False),
        User.role == Role.STUDENT,
        db.or_(
            User.full_name.ilike(f"%{q}%"),
            User.username.ilike(f"%{q}%"),
            User.student_id.ilike(f"%{q}%"),
            User.membership_id.ilike(f"%{q}%"),
        )
    ).limit(10).all()

    return jsonify([{
        "id":           m.id,
        "full_name":    m.full_name,
        "username":     m.username,
        "student_id":   m.student_id,
        "membership_id": m.membership_id,
        "active_issues": m.active_issues_count,
        "pending_fine": m.total_pending_fine,
    } for m in members])


# ─────────────────────────────────────────────────────────────────────────────
# Chart data for admin dashboard
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/charts/books-by-category")
@login_required
def books_by_category():
    """Books count grouped by category for doughnut chart."""
    rows = db.session.query(
        Category.name, func.count(Book.id).label("count")
    ).join(Book, Book.category_id == Category.id)\
     .filter(Book.is_deleted.is_(False), Category.is_deleted.is_(False))\
     .group_by(Category.name).all()

    uncategorised = Book.query.filter_by(is_deleted=False, category_id=None).count()
    labels  = [r.name for r in rows]
    data    = [r.count for r in rows]
    if uncategorised:
        labels.append("Uncategorised")
        data.append(uncategorised)

    return jsonify({"labels": labels, "data": data})


@api_bp.route("/charts/issue-trend")
@login_required
def issue_trend():
    """Issues per day for the last 30 days (line chart)."""
    now   = datetime.now(timezone.utc)
    start = now - timedelta(days=29)

    rows = db.session.query(
        func.date(Issue.issue_date).label("day"),
        func.count(Issue.id).label("count")
    ).filter(Issue.issue_date >= start)\
     .group_by(func.date(Issue.issue_date))\
     .order_by("day").all()

    day_map = {str(r.day): r.count for r in rows}
    labels, data = [], []
    for i in range(30):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append((start + timedelta(days=i)).strftime("%d %b"))
        data.append(day_map.get(d, 0))

    return jsonify({"labels": labels, "data": data})


@api_bp.route("/charts/fine-summary")
@login_required
def fine_summary():
    """Fine amounts by status for bar chart."""
    pending = db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.PENDING).scalar() or 0
    paid    = db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.PAID).scalar() or 0
    waived  = db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.WAIVED).scalar() or 0

    return jsonify({
        "labels": ["Pending", "Paid", "Waived"],
        "data":   [round(pending, 2), round(paid, 2), round(waived, 2)],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Notifications badge count
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/notifications/count")
@login_required
def notifications_count():
    """Return unread notification count for the current user."""
    from models import Notification
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": unread})


# ─────────────────────────────────────────────────────────────────────────────
# Book detail (for modal)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/books/<int:book_id>")
@login_required
def book_detail(book_id):
    book = Book.query.filter_by(id=book_id, is_deleted=False).first_or_404()
    
    ratings = book.reviews.all()
    avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else None
    
    return jsonify({
        "id":              book.id,
        "title":           book.title,
        "author":          book.author,
        "isbn":            book.isbn,
        "publisher":       book.publisher,
        "pub_year":        book.pub_year,
        "description":     book.description,
        "available_copies": book.available_copies,
        "total_copies":    book.total_copies,
        "status":          book.status,
        "category":        book.category.name if book.category else None,
        "cover_image":     book.cover_image,
        "review_count":    len(ratings),
        "avg_rating":      avg_rating,
    })
