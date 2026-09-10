"""
Authentication Blueprint – login, logout, register.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request
)
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User, Role, SystemSettings
from forms import LoginForm, RegisterForm
from utils import log_activity, generate_membership_id
from models import ActivityType

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _role_redirect(current_user)

    form = LoginForm()
    if form.validate_on_submit():
        # Accept username OR email
        identifier = form.username.data.strip()
        user = (
            User.query.filter_by(username=identifier, is_deleted=False).first()
            or User.query.filter_by(email=identifier, is_deleted=False).first()
        )

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Your account has been deactivated. Contact the admin.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)
            log_activity(ActivityType.LOGIN, f"{user.full_name} logged in")
            db.session.commit()

            # Honour "next" param
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return _role_redirect(user)
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_activity(ActivityType.LOGOUT, f"{current_user.full_name} logged out")
    db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Check if registration is allowed
    allow = SystemSettings.get("allow_registration", "True")
    if allow and allow.lower() == "false":
        flash("Public registration is currently disabled.", "warning")
        return redirect(url_for("auth.login"))

    if current_user.is_authenticated:
        return _role_redirect(current_user)

    form = RegisterForm()
    if form.validate_on_submit():
        membership_id = generate_membership_id()
        user = User(
            full_name     = form.full_name.data.strip(),
            username      = form.username.data.strip(),
            email         = form.email.data.strip().lower(),
            role          = Role.STUDENT,
            student_id    = form.student_id.data.strip() or None,
            department    = form.department.data.strip() or None,
            course        = form.course.data.strip() or None,
            membership_id = membership_id,
            max_books     = int(SystemSettings.get("max_books_student", 3)),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


# ── Helper ────────────────────────────────────────────────────────────────────

def _role_redirect(user):
    """Redirect to the appropriate dashboard based on role."""
    if user.role == Role.SUPER_ADMIN:
        return redirect(url_for("admin.dashboard"))
    elif user.role == Role.LIBRARIAN:
        return redirect(url_for("librarian.dashboard"))
    else:
        return redirect(url_for("student.dashboard"))
