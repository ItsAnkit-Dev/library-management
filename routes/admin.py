"""
Admin Blueprint – dashboard, books, members, categories,
                   issues, fines, settings, reports, activity log.
"""

import io
from datetime import timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, send_file
)
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from models import (
    db, User, Book, Category, Issue, Fine,
    ActivityLog, SystemSettings,
    Role, BookStatus, IssueStatus, FineStatus, ActivityType
)
from forms import (
    BookForm, CategoryForm, MemberForm, SettingsForm,
    FinePaymentForm, FineWaiveForm
)
from utils import (
    admin_required, log_activity, save_cover_image,
    generate_qr_code, update_issue_fines,
    export_issues_csv, export_fines_csv,
    get_int_setting, utcnow
)

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    update_issue_fines()

    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "total_books":     Book.query.filter_by(is_deleted=False).count(),
        "available_books": Book.query.filter_by(is_deleted=False, status=BookStatus.AVAILABLE).count(),
        "issued_books":    Issue.query.filter(Issue.status.in_([IssueStatus.ISSUED, IssueStatus.OVERDUE])).count(),
        "total_members":   User.query.filter_by(role=Role.STUDENT, is_deleted=False).count(),
        "active_librarians": User.query.filter_by(role=Role.LIBRARIAN, is_deleted=False, is_active=True).count(),
        "overdue_books":   Issue.query.filter_by(status=IssueStatus.OVERDUE).count(),
        "fine_this_month": db.session.query(func.sum(Fine.amount))
                             .filter(Fine.status == FineStatus.PAID,
                                     Fine.paid_at >= month_start).scalar() or 0,
        "total_categories": Category.query.filter_by(is_deleted=False).count(),
    }

    # Recent activities (last 20)
    recent_activities = ActivityLog.query\
        .order_by(desc(ActivityLog.created_at))\
        .limit(20).all()

    # Overdue issues for alert
    overdue_issues = Issue.query.filter_by(status=IssueStatus.OVERDUE)\
        .order_by(Issue.due_date).limit(5).all()

    # Due soon (next 2 days)
    due_soon = Issue.query.filter(
        Issue.status == IssueStatus.ISSUED,
        Issue.due_date <= now + timedelta(days=2),
        Issue.due_date >= now
    ).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_activities=recent_activities,
        overdue_issues=overdue_issues,
        due_soon=due_soon,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Book Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/books")
@login_required
@admin_required
def books():
    q          = request.args.get("q", "").strip()
    category   = request.args.get("category", 0, type=int)
    status     = request.args.get("status", "")
    page       = request.args.get("page", 1, type=int)

    query = Book.query.filter_by(is_deleted=False)

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like))
        )
    if category:
        query = query.filter_by(category_id=category)
    if status:
        query = query.filter_by(status=status)

    books_page = query.order_by(Book.title).paginate(page=page, per_page=15, error_out=False)
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name).all()

    return render_template(
        "admin/books.html",
        books=books_page,
        categories=categories,
        q=q, selected_category=category, selected_status=status
    )


@admin_bp.route("/books/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_book():
    form = BookForm()
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name).all()
    form.category_id.choices = [(0, "— No Category —")] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        cover = "default_cover.png"
        if form.cover_image.data:
            cover = save_cover_image(form.cover_image.data)

        book = Book(
            title          = form.title.data.strip(),
            author         = form.author.data.strip(),
            isbn           = form.isbn.data.strip(),
            publisher      = form.publisher.data,
            pub_year       = form.pub_year.data,
            edition        = form.edition.data,
            language       = form.language.data or "English",
            pages          = form.pages.data,
            description    = form.description.data,
            total_copies   = form.total_copies.data,
            available_copies = form.total_copies.data,
            category_id    = form.category_id.data or None,
            cover_image    = cover,
            added_by_id    = current_user.id,
        )
        db.session.add(book)
        db.session.flush()
        generate_qr_code(book.isbn, book.id)
        log_activity(ActivityType.BOOK_ADD, f"Added book: {book.title}", book_id=book.id)
        db.session.commit()
        flash(f"Book '{book.title}' added successfully!", "success")
        return redirect(url_for("admin.books"))

    return render_template("admin/book_form.html", form=form, title="Add Book", book=None)


@admin_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.filter_by(id=book_id, is_deleted=False).first_or_404()
    form = BookForm(obj=book)
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name).all()
    form.category_id.choices = [(0, "— No Category —")] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        book.title       = form.title.data.strip()
        book.author      = form.author.data.strip()
        book.isbn        = form.isbn.data.strip()
        book.publisher   = form.publisher.data
        book.pub_year    = form.pub_year.data
        book.edition     = form.edition.data
        book.language    = form.language.data
        book.pages       = form.pages.data
        book.description = form.description.data
        book.category_id = form.category_id.data or None

        # Adjust available_copies proportionally if total_copies changed
        diff = form.total_copies.data - book.total_copies
        book.total_copies     = form.total_copies.data
        book.available_copies = max(0, book.available_copies + diff)
        book.status = BookStatus.AVAILABLE if book.available_copies > 0 else BookStatus.ISSUED

        if form.cover_image.data:
            book.cover_image = save_cover_image(form.cover_image.data)

        generate_qr_code(book.isbn, book.id)
        log_activity(ActivityType.BOOK_EDIT, f"Edited book: {book.title}", book_id=book.id)
        db.session.commit()
        flash("Book updated successfully!", "success")
        return redirect(url_for("admin.books"))

    return render_template("admin/book_form.html", form=form, title="Edit Book", book=book)


@admin_bp.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.filter_by(id=book_id, is_deleted=False).first_or_404()
    book.is_deleted = True
    log_activity(ActivityType.BOOK_DELETE, f"Deleted book: {book.title}", book_id=book.id)
    db.session.commit()
    flash(f"Book '{book.title}' removed (soft delete).", "info")
    return redirect(url_for("admin.books"))


# ─────────────────────────────────────────────────────────────────────────────
# Category Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/categories")
@login_required
@admin_required
def categories():
    cats = Category.query.filter_by(is_deleted=False).order_by(Category.name).all()
    form = CategoryForm()
    return render_template("admin/categories.html", categories=cats, form=form)


@admin_bp.route("/categories/add", methods=["POST"])
@login_required
@admin_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(
            name        = form.name.data.strip(),
            description = form.description.data,
            color       = form.color.data or "#6366f1",
            icon        = form.icon.data or "fa-book",
        )
        db.session.add(cat)
        db.session.commit()
        flash(f"Category '{cat.name}' added.", "success")
    else:
        for field, errors in form.errors.items():
            flash(f"{field}: {', '.join(errors)}", "danger")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_category(cat_id):
    cat  = Category.query.filter_by(id=cat_id, is_deleted=False).first_or_404()
    form = CategoryForm()
    if form.validate_on_submit():
        cat.name        = form.name.data.strip()
        cat.description = form.description.data
        cat.color       = form.color.data or cat.color
        cat.icon        = form.icon.data or cat.icon
        db.session.commit()
        flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_category(cat_id):
    cat = Category.query.filter_by(id=cat_id, is_deleted=False).first_or_404()
    cat.is_deleted = True
    db.session.commit()
    flash(f"Category '{cat.name}' deleted.", "info")
    return redirect(url_for("admin.categories"))


# ─────────────────────────────────────────────────────────────────────────────
# Member Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/members")
@login_required
@admin_required
def members():
    q    = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    page = request.args.get("page", 1, type=int)

    query = User.query.filter_by(is_deleted=False)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            User.full_name.ilike(like),
            User.username.ilike(like),
            User.email.ilike(like),
            User.student_id.ilike(like),
        ))
    if role:
        query = query.filter_by(role=role)

    members_page = query.order_by(User.full_name).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/members.html", members=members_page, q=q, selected_role=role)


@admin_bp.route("/members/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_member():
    from utils import generate_membership_id
    form = MemberForm()
    if form.validate_on_submit():
        # Validate unique username/email
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken.", "danger")
            return render_template("admin/member_form.html", form=form, title="Add Member", member=None)
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
            return render_template("admin/member_form.html", form=form, title="Add Member", member=None)

        user = User(
            full_name     = form.full_name.data.strip(),
            username      = form.username.data.strip(),
            email         = form.email.data.strip().lower(),
            role          = form.role.data,
            phone         = form.phone.data,
            address       = form.address.data,
            student_id    = form.student_id.data or None,
            membership_id = generate_membership_id(),
            department    = form.department.data,
            course        = form.course.data,
            max_books     = form.max_books.data or get_int_setting("max_books_student", 3),
            is_active     = form.is_active.data,
        )
        pwd = form.password.data or "library@123"
        user.set_password(pwd)
        db.session.add(user)
        log_activity(ActivityType.MEMBER_ADD, f"Added member: {user.full_name}")
        db.session.commit()
        flash(f"Member '{user.full_name}' added (default pwd: {pwd if not form.password.data else '****'}).", "success")
        return redirect(url_for("admin.members"))

    return render_template("admin/member_form.html", form=form, title="Add Member", member=None)


@admin_bp.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_member(member_id):
    member = User.query.filter_by(id=member_id, is_deleted=False).first_or_404()
    form   = MemberForm(obj=member)

    if form.validate_on_submit():
        member.full_name  = form.full_name.data.strip()
        member.username   = form.username.data.strip()
        member.email      = form.email.data.strip().lower()
        member.role       = form.role.data
        member.phone      = form.phone.data
        member.address    = form.address.data
        member.student_id = form.student_id.data or None
        member.department = form.department.data
        member.course     = form.course.data
        member.max_books  = form.max_books.data or member.max_books
        member.is_active  = form.is_active.data
        if form.password.data:
            member.set_password(form.password.data)
        log_activity(ActivityType.MEMBER_EDIT, f"Edited member: {member.full_name}")
        db.session.commit()
        flash("Member updated!", "success")
        return redirect(url_for("admin.members"))

    return render_template("admin/member_form.html", form=form, title="Edit Member", member=member)


@admin_bp.route("/members/<int:member_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_member(member_id):
    member = User.query.filter_by(id=member_id, is_deleted=False).first_or_404()
    member.is_active = not member.is_active
    db.session.commit()
    state = "activated" if member.is_active else "deactivated"
    flash(f"Member {member.full_name} {state}.", "info")
    return redirect(url_for("admin.members"))


@admin_bp.route("/members/<int:member_id>")
@login_required
@admin_required
def member_detail(member_id):
    member  = User.query.filter_by(id=member_id, is_deleted=False).first_or_404()
    issues  = Issue.query.filter_by(member_id=member_id).order_by(desc(Issue.issue_date)).all()
    fines   = Fine.query.filter_by(member_id=member_id).order_by(desc(Fine.created_at)).all()
    return render_template("admin/member_detail.html", member=member, issues=issues, fines=fines)


# ─────────────────────────────────────────────────────────────────────────────
# Issues (view all)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/issues")
@login_required
@admin_required
def issues():
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
    return render_template("admin/issues.html", issues=issues_page,
                           selected_status=status, q=q)


# ─────────────────────────────────────────────────────────────────────────────
# Fine Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/fines")
@login_required
@admin_required
def fines():
    status = request.args.get("status", "")
    page   = request.args.get("page", 1, type=int)

    query = Fine.query
    if status:
        query = query.filter_by(status=status)

    fines_page = query.order_by(desc(Fine.created_at)).paginate(page=page, per_page=20, error_out=False)
    pay_form   = FinePaymentForm()
    waive_form = FineWaiveForm()
    return render_template("admin/fines.html", fines=fines_page,
                           pay_form=pay_form, waive_form=waive_form,
                           selected_status=status)


@admin_bp.route("/fines/<int:fine_id>/pay", methods=["POST"])
@login_required
@admin_required
def pay_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)
    fine.status    = FineStatus.PAID
    fine.paid_at   = utcnow()
    fine.paid_by_id = current_user.id
    log_activity(ActivityType.FINE_PAY, f"Fine ₹{fine.amount} paid for member {fine.member_id}")
    db.session.commit()
    flash(f"Fine of ₹{fine.amount:.2f} marked as paid.", "success")
    return redirect(url_for("admin.fines"))


@admin_bp.route("/fines/<int:fine_id>/waive", methods=["POST"])
@login_required
@admin_required
def waive_fine(fine_id):
    fine = Fine.query.get_or_404(fine_id)
    form = FineWaiveForm()
    if form.validate_on_submit():
        fine.status       = FineStatus.WAIVED
        fine.notes        = form.reason.data
        fine.waived_by_id = current_user.id
        log_activity(ActivityType.FINE_WAIVE, f"Fine ₹{fine.amount} waived for member {fine.member_id}")
        db.session.commit()
        flash(f"Fine of ₹{fine.amount:.2f} waived.", "info")
    return redirect(url_for("admin.fines"))


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    form = SettingsForm(
        library_name       = SystemSettings.get("library_name",       current_app.config["LIBRARY_NAME"]),
        library_tagline    = SystemSettings.get("library_tagline",    current_app.config["LIBRARY_TAGLINE"]),
        library_email      = SystemSettings.get("library_email",      current_app.config["LIBRARY_EMAIL"]),
        library_phone      = SystemSettings.get("library_phone",      current_app.config["LIBRARY_PHONE"]),
        library_address    = SystemSettings.get("library_address",    current_app.config["LIBRARY_ADDRESS"]),
        fine_per_day       = float(SystemSettings.get("fine_per_day",      current_app.config["FINE_PER_DAY"])),
        max_fine_limit     = float(SystemSettings.get("max_fine_limit",    current_app.config["MAX_FINE_LIMIT"])),
        max_books_student  = int(SystemSettings.get("max_books_student",   current_app.config["MAX_BOOKS_PER_STUDENT"])),
        default_issue_days = int(SystemSettings.get("default_issue_days",  current_app.config["DEFAULT_ISSUE_DAYS"])),
        renew_days         = int(SystemSettings.get("renew_days",          current_app.config["RENEW_EXTENSION_DAYS"])),
        max_fine_block     = float(SystemSettings.get("max_fine_block",    current_app.config["MAX_FINE_BEFORE_BLOCK"])),
        allow_registration = SystemSettings.get("allow_registration", "True").lower() == "true",
    )

    if form.validate_on_submit():
        mapping = {
            "library_name":       form.library_name.data,
            "library_tagline":    form.library_tagline.data,
            "library_email":      form.library_email.data,
            "library_phone":      form.library_phone.data,
            "library_address":    form.library_address.data,
            "fine_per_day":       form.fine_per_day.data,
            "max_fine_limit":     form.max_fine_limit.data,
            "max_books_student":  form.max_books_student.data,
            "default_issue_days": form.default_issue_days.data,
            "renew_days":         form.renew_days.data,
            "max_fine_block":     form.max_fine_block.data,
            "allow_registration": form.allow_registration.data,
        }
        for key, val in mapping.items():
            SystemSettings.set(key, val)
        log_activity(ActivityType.SETTINGS, "Settings updated")
        flash("Settings saved successfully!", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", form=form)


# ─────────────────────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/activity-log")
@login_required
@admin_required
def activity_log():
    page = request.args.get("page", 1, type=int)
    logs = ActivityLog.query.order_by(desc(ActivityLog.created_at))\
               .paginate(page=page, per_page=30, error_out=False)
    return render_template("admin/activity_log.html", logs=logs)


# ─────────────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    # Most popular books
    popular = db.session.query(
        Book, func.count(Issue.id).label("borrow_count")
    ).join(Issue).filter(Book.is_deleted.is_(False))\
     .group_by(Book.id).order_by(desc("borrow_count")).limit(10).all()

    # Fine summary
    fine_summary = {
        "total":   db.session.query(func.sum(Fine.amount)).scalar() or 0,
        "pending": db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.PENDING).scalar() or 0,
        "paid":    db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.PAID).scalar() or 0,
        "waived":  db.session.query(func.sum(Fine.amount)).filter_by(status=FineStatus.WAIVED).scalar() or 0,
    }

    overdue = Issue.query.filter_by(status=IssueStatus.OVERDUE)\
                  .order_by(Issue.due_date).all()

    return render_template(
        "reports/index.html",
        popular=popular,
        fine_summary=fine_summary,
        overdue=overdue,
    )


@admin_bp.route("/reports/export/issues")
@login_required
@admin_required
def export_issues():
    issues = Issue.query.order_by(desc(Issue.issue_date)).all()
    csv_data = export_issues_csv(issues)
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="issues_report.csv",
    )


@admin_bp.route("/reports/export/fines")
@login_required
@admin_required
def export_fines():
    fines = Fine.query.order_by(desc(Fine.created_at)).all()
    csv_data = export_fines_csv(fines)
    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="fines_report.csv",
    )
