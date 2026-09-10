"""
Student Blueprint – dashboard, my books, history, wishlist/reservations,
                    reviews, reading goal, fine payment, notifications.
"""

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import desc

from models import (
    db, Book, Issue, Fine, Reservation, Category,
    IssueStatus, FineStatus, ReservationStatus, ActivityType,
    BookReview, ReadingGoal, Notification
)
from utils import student_required, log_activity, update_issue_fines, utcnow, get_student_recommendations

student_bp = Blueprint("student", __name__, template_folder="../templates/student")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    update_issue_fines()

    now = utcnow()

    current_issues = Issue.query.filter(
        Issue.member_id == current_user.id,
        Issue.status.in_([IssueStatus.ISSUED, IssueStatus.OVERDUE])
    ).order_by(Issue.due_date).all()

    due_soon = [i for i in current_issues
                if 0 <= (i.due_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days <= 2]

    total_fine = current_user.total_pending_fine

    # Recent history (last 5 returned)
    recent_history = Issue.query.filter_by(
        member_id=current_user.id,
        status=IssueStatus.RETURNED
    ).order_by(desc(Issue.return_date)).limit(5).all()

    # Recommendations
    recommendations = get_student_recommendations(current_user.id, limit=4)

    # Reading Goal Progress
    current_year = now.year
    current_month = now.month
    reading_goal = ReadingGoal.query.filter_by(
        user_id=current_user.id, year=current_year, month=current_month
    ).first()

    # Books returned this month
    books_read_this_month = Issue.query.filter(
        Issue.member_id == current_user.id,
        Issue.status == IssueStatus.RETURNED,
        db.extract('year', Issue.return_date) == current_year,
        db.extract('month', Issue.return_date) == current_month
    ).count()

    return render_template(
        "student/dashboard.html",
        current_issues=current_issues,
        due_soon=due_soon,
        total_fine=total_fine,
        recent_history=recent_history,
        recommendations=recommendations,
        reading_goal=reading_goal,
        books_read_this_month=books_read_this_month,
    )



# ─────────────────────────────────────────────────────────────────────────────
# My Books (currently issued)
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/my-books")
@login_required
@student_required
def my_books():
    issues = Issue.query.filter(
        Issue.member_id == current_user.id,
        Issue.status.in_([IssueStatus.ISSUED, IssueStatus.OVERDUE])
    ).order_by(Issue.due_date).all()

    return render_template("student/my_books.html", issues=issues)


# ─────────────────────────────────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/history")
@login_required
@student_required
def history():
    page = request.args.get("page", 1, type=int)
    issues = Issue.query.filter_by(member_id=current_user.id)\
        .order_by(desc(Issue.issue_date))\
        .paginate(page=page, per_page=15, error_out=False)

    fines = Fine.query.filter_by(member_id=current_user.id)\
        .order_by(desc(Fine.created_at)).all()

    return render_template("student/history.html", issues=issues, fines=fines)


# ─────────────────────────────────────────────────────────────────────────────
# Browse Books
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/browse")
@login_required
@student_required
def browse():
    q        = request.args.get("q", "").strip()
    cat_id   = request.args.get("category", 0, type=int)
    avail    = request.args.get("available", "")
    page     = request.args.get("page", 1, type=int)

    from models import Book
    query = Book.query.filter_by(is_deleted=False)

    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Book.title.ilike(like),
            Book.author.ilike(like),
            Book.isbn.ilike(like),
        ))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if avail:
        query = query.filter(Book.available_copies > 0)

    books      = query.order_by(Book.title).paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name).all()

    # Build set of reserved book IDs for this student
    reserved_ids = {r.book_id for r in Reservation.query.filter_by(
        member_id=current_user.id, status=ReservationStatus.PENDING
    ).all()}

    return render_template(
        "student/browse.html",
        books=books,
        categories=categories,
        q=q, selected_category=cat_id, avail=avail,
        reserved_ids=reserved_ids,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/recommendations")
@login_required
@student_required
def recommendations():
    # Show more recommendations on a dedicated page (e.g. up to 12)
    books = get_student_recommendations(current_user.id, limit=12)
    
    # Build set of reserved book IDs for this student (to disable 'add to wishlist' if needed)
    reserved_ids = {r.book_id for r in Reservation.query.filter_by(
        member_id=current_user.id, status=ReservationStatus.PENDING
    ).all()}
    
    return render_template("student/recommendations.html", books=books, reserved_ids=reserved_ids)


# ─────────────────────────────────────────────────────────────────────────────
# Wishlist / Reservations
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/wishlist")
@login_required
@student_required
def wishlist():
    reservations = Reservation.query.filter_by(
        member_id=current_user.id,
        status=ReservationStatus.PENDING
    ).order_by(desc(Reservation.reserved_at)).all()
    return render_template("student/wishlist.html", reservations=reservations)


@student_bp.route("/reserve/<int:book_id>", methods=["POST"])
@login_required
@student_required
def reserve_book(book_id):
    book = Book.query.filter_by(id=book_id, is_deleted=False).first_or_404()

    # Check not already reserved
    existing = Reservation.query.filter_by(
        member_id=current_user.id,
        book_id=book_id,
        status=ReservationStatus.PENDING
    ).first()
    if existing:
        flash("You already have a reservation for this book.", "info")
        return redirect(url_for("student.wishlist"))

    # Check not already issued
    issued = Issue.query.filter_by(
        member_id=current_user.id,
        book_id=book_id,
        status=IssueStatus.ISSUED
    ).first()
    if issued:
        flash("You already have this book issued.", "info")
        return redirect(url_for("student.browse"))

    reservation = Reservation(
        member_id = current_user.id,
        book_id   = book_id,
        status    = ReservationStatus.PENDING,
    )
    db.session.add(reservation)
    log_activity(ActivityType.RESERVE, f"Reserved '{book.title}'", book_id=book_id)
    db.session.commit()
    flash(f"'{book.title}' added to your wishlist. We'll notify you when it's available.", "success")
    return redirect(url_for("student.wishlist"))


@student_bp.route("/reserve/<int:reservation_id>/cancel", methods=["POST"])
@login_required
@student_required
def cancel_reservation(reservation_id):
    reservation = Reservation.query.filter_by(
        id=reservation_id, member_id=current_user.id
    ).first_or_404()
    reservation.status = ReservationStatus.CANCELLED
    db.session.commit()
    flash("Reservation cancelled.", "info")
    return redirect(url_for("student.wishlist"))


# ─────────────────────────────────────────────────────────────────────────────
# Fine Payment
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/pay-fine/<int:fine_id>", methods=["POST"])
@login_required
@student_required
def pay_fine(fine_id):
    fine = Fine.query.filter_by(id=fine_id, member_id=current_user.id, status=FineStatus.PENDING).first_or_404()
    
    # Mock payment processing
    fine.status = FineStatus.PAID
    fine.paid_at = utcnow()
    fine.paid_by_id = current_user.id
    
    log_activity(ActivityType.FINE_ONLINE, f"Paid fine of ₹{fine.amount} online", issue_id=fine.issue_id)
    db.session.commit()
    
    flash(f"Payment of ₹{fine.amount} successful!", "success")
    return redirect(request.referrer or url_for("student.history"))


# ─────────────────────────────────────────────────────────────────────────────
# Reading Goal
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/set-goal", methods=["POST"])
@login_required
@student_required
def set_goal():
    target = request.form.get("target", type=int)
    if not target or target < 1:
        flash("Invalid goal target.", "danger")
        return redirect(url_for("student.dashboard"))
        
    now = utcnow()
    goal = ReadingGoal.query.filter_by(
        user_id=current_user.id, year=now.year, month=now.month
    ).first()
    
    if goal:
        goal.target = target
        flash("Reading goal updated!", "success")
    else:
        goal = ReadingGoal(
            user_id=current_user.id, year=now.year, month=now.month, target=target
        )
        db.session.add(goal)
        flash("Reading goal set for this month!", "success")
        
    log_activity(ActivityType.GOAL_SET, f"Set reading goal to {target} books")
    db.session.commit()
    return redirect(url_for("student.dashboard"))


# ─────────────────────────────────────────────────────────────────────────────
# Book Reviews
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/review/<int:book_id>", methods=["POST"])
@login_required
@student_required
def submit_review(book_id):
    rating = request.form.get("rating", type=int)
    review_text = request.form.get("review", "").strip()
    
    if not rating or not (1 <= rating <= 5):
        flash("Invalid rating.", "danger")
        return redirect(request.referrer or url_for("student.history"))
        
    # Ensure they have returned this book
    issue = Issue.query.filter_by(
        member_id=current_user.id, book_id=book_id, status=IssueStatus.RETURNED
    ).first()
    
    if not issue:
        flash("You can only review books you have read and returned.", "warning")
        return redirect(request.referrer or url_for("student.history"))
        
    review = BookReview.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if review:
        review.rating = rating
        review.review = review_text
        flash("Review updated!", "success")
    else:
        review = BookReview(user_id=current_user.id, book_id=book_id, rating=rating, review=review_text)
        db.session.add(review)
        flash("Review submitted!", "success")
        
    log_activity(ActivityType.REVIEW, f"Rated book {book_id} {rating} stars", book_id=book_id)
    db.session.commit()
    
    return redirect(request.referrer or url_for("student.history"))


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

@student_bp.route("/notifications")
@login_required
@student_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Notification.created_at)).all()
    return render_template("student/notifications.html", notifications=notifs)


@student_bp.route("/notifications/read/<int:notif_id>", methods=["POST"])
@login_required
@student_required
def read_notification(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})

