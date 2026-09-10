"""
Utility functions for the Library Management System.
Includes: fine calculation, QR code generation, file helpers,
          activity logging, decorators, CSV/PDF export.
"""

import os
import csv
import io
import qrcode
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import current_app, abort, request
from flask_login import current_user
from models import db, ActivityLog, SystemSettings, Fine, Issue, FineStatus, IssueStatus, Role, Book, Reservation, ReservationStatus, Notification, NotificationType
from sqlalchemy import func, desc
from collections import Counter

# ─────────────────────────────────────────────────────────────────────────────
# Role-based access decorators
# ─────────────────────────────────────────────────────────────────────────────


def admin_required(f):
    """Restrict view to Super Admin only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.SUPER_ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def librarian_required(f):
    """Restrict view to Librarian or Super Admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in (
            Role.SUPER_ADMIN, Role.LIBRARIAN
        ):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Restrict view to Student role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.STUDENT:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# Settings helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    """Fetch a system setting, falling back to app config then default."""
    val = SystemSettings.get(key)
    if val is not None:
        return val
    # Try app config
    cfg_key = key.upper()
    return current_app.config.get(cfg_key, default)


def get_float_setting(key: str, default: float = 0.0) -> float:
    try:
        return float(get_setting(key, default))
    except (ValueError, TypeError):
        return default


def get_int_setting(key: str, default: int = 0) -> int:
    try:
        return int(get_setting(key, default))
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Fine calculation
# ─────────────────────────────────────────────────────────────────────────────

def calculate_fine(due_date: datetime, return_date: datetime = None) -> float:
    """
    Calculate the overdue fine.
    due_date and return_date should both be timezone-aware or naive.
    """
    fine_per_day = get_float_setting(
        "fine_per_day", current_app.config.get(
            "FINE_PER_DAY", 2.0))
    max_fine = get_float_setting(
        "max_fine_limit", current_app.config.get(
            "MAX_FINE_LIMIT", 200.0))

    ref_date = return_date or datetime.now(timezone.utc)

    # Make both timezone-aware
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    if ref_date.tzinfo is None:
        ref_date = ref_date.replace(tzinfo=timezone.utc)

    if ref_date <= due_date:
        return 0.0

    days_late = (ref_date - due_date).days
    fine = days_late * fine_per_day
    return min(fine, max_fine)


def update_issue_fines():
    """
    Called periodically (or on dashboard load) to create/update Fine records
    for all overdue issues, and generate due/overdue notifications.
    """
    now = datetime.now(timezone.utc)

    # 1. Handle Overdue Issues
    overdue_issues = Issue.query.filter(
        Issue.status == IssueStatus.ISSUED,
        Issue.due_date < now,
    ).all()

    for issue in overdue_issues:
        issue.status = IssueStatus.OVERDUE

        # Generate overdue notification
        notif = Notification(
            user_id=issue.member_id,
            type=NotificationType.OVERDUE_ALERT,
            title="Book Overdue",
            message=f"Your book '{
                issue.book.title}' is overdue. Please return it as soon as possible.")
        db.session.add(notif)

        fine_amount = calculate_fine(issue.due_date)
        if fine_amount > 0:
            if issue.fine is None:
                fine = Fine(
                    issue_id=issue.id,
                    member_id=issue.member_id,
                    amount=fine_amount,
                    reason="Overdue",
                    status=FineStatus.PENDING,
                )
                db.session.add(fine)
            else:
                if issue.fine.status == FineStatus.PENDING:
                    issue.fine.amount = fine_amount

    # 2. Handle Due Soon Reminders
    due_soon_issues = Issue.query.filter(
        Issue.status == IssueStatus.ISSUED,
        Issue.due_date >= now,
        Issue.due_date <= now + timedelta(days=2)
    ).all()

    for issue in due_soon_issues:
        # Check if reminder already sent recently (last 2 days)
        cutoff = now - timedelta(days=2)
        existing = Notification.query.filter(
            Notification.user_id == issue.member_id,
            Notification.type == NotificationType.DUE_REMINDER,
            Notification.created_at >= cutoff,
            Notification.message.like(f"%'{issue.book.title}'%")
        ).first()

        if not existing:
            notif = Notification(
                user_id=issue.member_id,
                type=NotificationType.DUE_REMINDER,
                title="Book Due Soon",
                message=f"Your book '{
                    issue.book.title}' is due on {
                    issue.due_date.strftime('%d %b %Y')}.")
            db.session.add(notif)

    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Activity logging
# ─────────────────────────────────────────────────────────────────────────────

def log_activity(activity: str, description: str = "",
                 book_id: int = None, issue_id: int = None):
    """Insert an ActivityLog row for the current user."""
    user_id = current_user.id if current_user.is_authenticated else None
    ip = request.remote_addr if request else None
    log = ActivityLog(
        user_id=user_id,
        activity=activity,
        description=description,
        ip_address=ip,
        book_id=book_id,
        issue_id=issue_id,
    )  # type: ignore
    db.session.add(log)
    # Commit will be handled by the caller (inside a larger transaction)


# ─────────────────────────────────────────────────────────────────────────────
# File upload helpers
# ─────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get(
        "ALLOWED_EXTENSIONS", {
            "png", "jpg", "jpeg", "gif", "webp"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_cover_image(file_obj) -> str:
    """Save an uploaded cover image and return the filename."""
    import uuid
    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file_obj.save(os.path.join(folder, filename))
    return filename


# ─────────────────────────────────────────────────────────────────────────────
# QR Code generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_qr_code(book_isbn: str, book_id: int) -> str:
    """Generate a QR code PNG for a book and return the filename."""
    qr_dir = os.path.join(current_app.static_folder, "uploads", "qr")
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"qr_{book_isbn}.png"
    filepath = os.path.join(qr_dir, filename)

    if not os.path.exists(filepath):
        # Encode a URL to the book's detail page
        data = f"BOOK|{book_id}|{book_isbn}"
        img = qrcode.make(data)
        img.save(filepath)

    return filename


# ─────────────────────────────────────────────────────────────────────────────
# CSV Export
# ─────────────────────────────────────────────────────────────────────────────

def export_issues_csv(issues):
    """Return a CSV string for issued books report."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Issue ID", "Member", "Book Title", "ISBN",
        "Issue Date", "Due Date", "Return Date", "Status", "Fine (₹)"
    ])
    for issue in issues:
        fine_amt = issue.fine.amount if issue.fine else 0
        writer.writerow([
            issue.id,
            issue.member.full_name,
            issue.book.title,
            issue.book.isbn,
            issue.issue_date.strftime("%Y-%m-%d"),
            issue.due_date.strftime("%Y-%m-%d"),
            issue.return_date.strftime("%Y-%m-%d") if issue.return_date else "",
            issue.status,
            f"{fine_amt:.2f}",
        ])
    return output.getvalue()


def export_fines_csv(fines):
    """Return a CSV string for fines report."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Fine ID", "Member", "Book", "Amount (₹)",
        "Reason", "Status", "Created", "Paid At"
    ])
    for fine in fines:
        writer.writerow([
            fine.id,
            fine.member.full_name,
            fine.issue.book.title if fine.issue else "",
            f"{fine.amount:.2f}",
            fine.reason,
            fine.status,
            fine.created_at.strftime("%Y-%m-%d"),
            fine.paid_at.strftime("%Y-%m-%d") if fine.paid_at else "",
        ])
    return output.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Email simulation (console print)
# ─────────────────────────────────────────────────────────────────────────────

def send_overdue_email_simulation(member, issue):
    """
    Simulate sending an overdue email by printing to console.
    Replace with a real email backend in production.
    """
    days = issue.days_overdue
    print(
        f"\n[EMAIL] To: {member.email}\n"
        f"Subject: Overdue Book Reminder – {issue.book.title}\n"
        f"Dear {member.full_name},\n"
        f"Your book '{issue.book.title}' was due on "
        f"{issue.due_date.strftime('%d %b %Y')} ({days} day(s) ago).\n"
        f"Please return it to avoid additional fines.\n"
        f"Thank you,\nThe Library Team\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Date helpers
# ─────────────────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)


def format_date(dt: datetime, fmt: str = "%d %b %Y") -> str:
    if dt is None:
        return "—"
    return dt.strftime(fmt)


# ─────────────────────────────────────────────────────────────────────────────
# Membership ID generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_membership_id() -> str:
    from models import User
    count = User.query.filter(User.membership_id.isnot(None)).count()
    return f"LIB{(count + 1):05d}"


# ─────────────────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────────────────

def get_student_recommendations(user_id: int, limit: int = 6):
    """
    Generate personalized book recommendations for a student based on their past issues.
    Fallback to overall popular books.
    """
    # Get categories of past issued books
    past_issues = Issue.query.filter_by(member_id=user_id).all()
    past_cat_ids = [
        issue.book.category_id for issue in past_issues if issue.book.category_id]

    # Get wishlist books
    wishlist_reservations = Reservation.query.filter_by(
        member_id=user_id, status=ReservationStatus.PENDING
    ).all()
    wishlist_book_ids = {r.book_id for r in wishlist_reservations}

    # Get currently issued book ids to exclude them too
    issued_book_ids = {
        issue.book_id for issue in past_issues if issue.status in [
            IssueStatus.ISSUED,
            IssueStatus.OVERDUE]}

    exclude_ids = wishlist_book_ids.union(issued_book_ids)

    recommendations = []

    if past_cat_ids:
        # Determine top 2 categories
        top_cats = [
            cat_id for cat_id,
            _ in Counter(past_cat_ids).most_common(2)]

        # Find popular books in these categories not already issued/wishlisted
        cat_books = db.session.query(
            Book,
            func.count(
                Issue.id).label("issue_count")).outerjoin(
            Issue,
            Issue.book_id == Book.id) .filter(
                Book.is_deleted.is_(False),
                Book.category_id.in_(top_cats),
                ~Book.id.in_(exclude_ids)) .group_by(
                    Book.id) .order_by(
                        desc("issue_count")).limit(limit).all()

        recommendations.extend([b[0] for b in cat_books])

    # If not enough, fill with globally popular books
    if len(recommendations) < limit:
        needed = limit - len(recommendations)
        exclude_all = exclude_ids.union({b.id for b in recommendations})

        pop_books = db.session.query(
            Book, func.count(Issue.id).label("issue_count")
        ).outerjoin(Issue, Issue.book_id == Book.id)\
         .filter(Book.is_deleted.is_(False), ~Book.id.in_(exclude_all))\
         .group_by(Book.id)\
         .order_by(desc("issue_count")).limit(needed).all()

        recommendations.extend([b[0] for b in pop_books])

    return recommendations
