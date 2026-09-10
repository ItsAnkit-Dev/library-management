"""
Librarian Blueprint – dashboard, issue book, return book, renew.
Librarians and Super Admins can access these routes.
"""

from datetime import timedelta
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import desc

from models import (
    db, User, Book, Issue, Fine, Reservation,
    BookStatus, IssueStatus, FineStatus, ReservationStatus, ActivityType
)
from forms import IssueForm, ReturnForm
from utils import (
    librarian_required, log_activity, calculate_fine,
    update_issue_fines, get_int_setting, get_float_setting,
    utcnow, add_days
)

librarian_bp = Blueprint("librarian", __name__, template_folder="../templates/librarian")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@librarian_bp.route("/dashboard")
@login_required
@librarian_required
def dashboard():
    update_issue_fines()

    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    now         = utcnow()

    stats = {
        "today_issued":  Issue.query.filter(Issue.issue_date >= today_start).count(),
        "today_returned": Issue.query.filter(
            Issue.status == IssueStatus.RETURNED,
            Issue.return_date >= today_start
        ).count(),
        "pending_returns": Issue.query.filter(Issue.status.in_([IssueStatus.ISSUED, IssueStatus.OVERDUE])).count(),
        "overdue": Issue.query.filter_by(status=IssueStatus.OVERDUE).count(),
    }

    # Overdue issues
    overdue_issues = Issue.query.filter_by(status=IssueStatus.OVERDUE)\
        .order_by(Issue.due_date).limit(10).all()

    # Due soon (next 2 days)
    due_soon = Issue.query.filter(
        Issue.status == IssueStatus.ISSUED,
        Issue.due_date <= now + timedelta(days=2),
        Issue.due_date >= now
    ).order_by(Issue.due_date).limit(10).all()

    # Recent issues
    recent = Issue.query.order_by(desc(Issue.issue_date)).limit(10).all()

    return render_template(
        "librarian/dashboard.html",
        stats=stats,
        overdue_issues=overdue_issues,
        due_soon=due_soon,
        recent=recent,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Issue Book
# ─────────────────────────────────────────────────────────────────────────────

@librarian_bp.route("/issue", methods=["GET", "POST"])
@login_required
@librarian_required
def issue_book():
    form = IssueForm()

    if form.validate_on_submit():
        # Resolve member
        member_query = form.member_isbn.data.strip()
        member = (
            User.query.filter_by(username=member_query, is_deleted=False).first()
            or User.query.filter_by(student_id=member_query, is_deleted=False).first()
            or User.query.filter_by(membership_id=member_query, is_deleted=False).first()
        )
        if not member:
            flash(f"Member '{member_query}' not found.", "danger")
            return render_template("librarian/issue_book.html", form=form)

        if not member.is_active:
            flash("Member account is deactivated.", "danger")
            return render_template("librarian/issue_book.html", form=form)

        # Resolve book
        book_query = form.book_isbn.data.strip()
        book = (
            Book.query.filter_by(isbn=book_query, is_deleted=False).first()
            or Book.query.filter(Book.title.ilike(f"%{book_query}%"), Book.is_deleted.is_(False)).first()
        )
        if not book:
            flash(f"Book '{book_query}' not found.", "danger")
            return render_template("librarian/issue_book.html", form=form)

        # Validations
        max_fine_block = get_float_setting("max_fine_block", current_app.config["MAX_FINE_BEFORE_BLOCK"])
        if member.total_pending_fine > max_fine_block:
            flash(f"Member has unpaid fine of ₹{member.total_pending_fine:.2f}. Clear fines first.", "danger")
            return render_template("librarian/issue_book.html", form=form)

        max_books = member.max_books or get_int_setting("max_books_student", 3)
        if member.active_issues_count >= max_books:
            flash(f"Member has reached maximum book limit ({max_books}).", "danger")
            return render_template("librarian/issue_book.html", form=form)

        # Check already issued this book
        existing = Issue.query.filter_by(
            member_id=member.id, book_id=book.id,
            status=IssueStatus.ISSUED
        ).first()
        if existing:
            flash("Member already has this book issued.", "warning")
            return render_template("librarian/issue_book.html", form=form)

        if book.available_copies <= 0:
            flash("No available copies of this book.", "danger")
            return render_template("librarian/issue_book.html", form=form)

        # Create issue
        issue_days = get_int_setting("default_issue_days", current_app.config["DEFAULT_ISSUE_DAYS"])
        now = utcnow()
        issue = Issue(
            member_id    = member.id,
            book_id      = book.id,
            issued_by_id = current_user.id,
            issue_date   = now,
            due_date     = add_days(now, issue_days),
            status       = IssueStatus.ISSUED,
            notes        = form.notes.data,
        )
        book.available_copies -= 1
        if book.available_copies == 0:
            book.status = BookStatus.ISSUED

        # Fulfil any reservation
        reservation = Reservation.query.filter_by(
            member_id=member.id, book_id=book.id,
            status=ReservationStatus.PENDING
        ).first()
        if reservation:
            reservation.status       = ReservationStatus.FULFILLED
            reservation.fulfilled_at = now

        db.session.add(issue)
        log_activity(ActivityType.ISSUE,
                     f"Issued '{book.title}' to {member.full_name}",
                     book_id=book.id)
        db.session.commit()
        flash(f"Book '{book.title}' issued to {member.full_name}. Due: {issue.due_date.strftime('%d %b %Y')}", "success")
        return redirect(url_for("librarian.dashboard"))

    return render_template("librarian/issue_book.html", form=form)


# ─────────────────────────────────────────────────────────────────────────────
# Return Book
# ─────────────────────────────────────────────────────────────────────────────

@librarian_bp.route("/return", methods=["GET", "POST"])
@login_required
@librarian_required
def return_book():
    form = ReturnForm()

    # Search for active issues
    q          = request.args.get("q", "").strip()
    active_issues = []
    if q:
        active_issues = Issue.query.join(Book).join(User, Issue.member_id == User.id).filter(
            Issue.status.in_([IssueStatus.ISSUED, IssueStatus.OVERDUE]),
            db.or_(
                Book.isbn.ilike(f"%{q}%"),
                Book.title.ilike(f"%{q}%"),
                User.username.ilike(f"%{q}%"),
                User.student_id.ilike(f"%{q}%"),
            )
        ).order_by(Issue.due_date).all()

    if form.validate_on_submit():
        issue = Issue.query.get_or_404(int(form.issue_id.data))
        now   = utcnow()

        if form.mark_lost.data:
            issue.status      = IssueStatus.LOST
            issue.return_date = now
            issue.book.status = BookStatus.LOST
            # Charge full fine + lost fine
            fine_amount = get_float_setting("max_fine_limit", current_app.config["MAX_FINE_LIMIT"])
        else:
            issue.status      = IssueStatus.RETURNED
            issue.return_date = now
            issue.book.available_copies += 1
            issue.book.status = BookStatus.AVAILABLE
            fine_amount = calculate_fine(issue.due_date, now)

        if fine_amount > 0:
            if issue.fine:
                issue.fine.amount = fine_amount
                issue.fine.status = FineStatus.PENDING
            else:
                fine = Fine(
                    issue_id  = issue.id,
                    member_id = issue.member_id,
                    amount    = fine_amount,
                    reason    = "Lost" if form.mark_lost.data else "Overdue",
                    status    = FineStatus.PENDING,
                )
                db.session.add(fine)
            flash(f"Book returned. Fine of ₹{fine_amount:.2f} levied.", "warning")
        else:
            flash("Book returned successfully. No fine.", "success")

        log_activity(ActivityType.RETURN,
                     f"Returned '{issue.book.title}' from {issue.member.full_name}",
                     book_id=issue.book_id, issue_id=issue.id)
        db.session.commit()
        return redirect(url_for("librarian.return_book"))

    return render_template("librarian/return_book.html", form=form,
                           active_issues=active_issues, q=q)


# ─────────────────────────────────────────────────────────────────────────────
# Renew
# ─────────────────────────────────────────────────────────────────────────────

@librarian_bp.route("/renew/<int:issue_id>", methods=["POST"])
@login_required
@librarian_required
def renew(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    if issue.status not in (IssueStatus.ISSUED, IssueStatus.OVERDUE):
        flash("Cannot renew this issue.", "danger")
        return redirect(url_for("librarian.dashboard"))

    renew_days    = get_int_setting("renew_days", current_app.config["RENEW_EXTENSION_DAYS"])
    issue.due_date     = add_days(issue.due_date, renew_days)
    issue.renewed_date = utcnow()
    issue.renew_count += 1
    issue.status       = IssueStatus.ISSUED  # Reset overdue if renewed

    log_activity(ActivityType.RENEW,
                 f"Renewed '{issue.book.title}' for {issue.member.full_name}",
                 book_id=issue.book_id, issue_id=issue.id)
    db.session.commit()
    flash(f"Renewed! New due date: {issue.due_date.strftime('%d %b %Y')}", "success")
    return redirect(request.referrer or url_for("librarian.dashboard"))


# ─────────────────────────────────────────────────────────────────────────────
# All active issues (librarian view)
# ─────────────────────────────────────────────────────────────────────────────

@librarian_bp.route("/issues")
@login_required
@librarian_required
def all_issues():
    status = request.args.get("status", "")
    q      = request.args.get("q", "").strip()
    page   = request.args.get("page", 1, type=int)

    query = Issue.query.join(Book).join(User, Issue.member_id == User.id)
    if status:
        query = query.filter(Issue.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Book.title.ilike(like),
            User.full_name.ilike(like),
            Book.isbn.ilike(like),
        ))

    issues_page = query.order_by(desc(Issue.issue_date)).paginate(page=page, per_page=20, error_out=False)
    return render_template("librarian/all_issues.html", issues=issues_page,
                           selected_status=status, q=q)
