"""
WTForms form definitions for the Library Management System.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField,
    TextAreaField, IntegerField, FloatField, HiddenField,
    SubmitField, EmailField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Optional,
    NumberRange, ValidationError
)
from models import User, Book


# ─────────────────────────────────────────────────────────────────────────────
# Auth Forms
# ─────────────────────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    username = StringField("Username / Email",
                           validators=[DataRequired(), Length(min=3, max=120)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit   = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    full_name  = StringField("Full Name",   validators=[DataRequired(), Length(min=2, max=120)])
    username   = StringField("Username",    validators=[DataRequired(), Length(min=3, max=80)])
    email      = EmailField("Email",        validators=[DataRequired(), Email()])
    password   = PasswordField("Password",  validators=[DataRequired(), Length(min=6)])
    confirm    = PasswordField("Confirm",   validators=[DataRequired(), EqualTo("password")])
    student_id = StringField("Student ID",  validators=[Optional(), Length(max=50)])
    department = StringField("Department",  validators=[Optional(), Length(max=100)])
    course     = StringField("Course",      validators=[Optional(), Length(max=100)])
    submit     = SubmitField("Register")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")


# ─────────────────────────────────────────────────────────────────────────────
# Book Forms
# ─────────────────────────────────────────────────────────────────────────────

class BookForm(FlaskForm):
    title         = StringField("Title",       validators=[DataRequired(), Length(max=200)])
    author        = StringField("Author",      validators=[DataRequired(), Length(max=200)])
    isbn          = StringField("ISBN",        validators=[DataRequired(), Length(max=20)])
    publisher     = StringField("Publisher",   validators=[Optional(), Length(max=150)])
    pub_year      = IntegerField("Pub Year",   validators=[Optional(), NumberRange(min=1000, max=2100)])
    edition       = StringField("Edition",     validators=[Optional(), Length(max=50)])
    language      = StringField("Language",    validators=[Optional(), Length(max=50)])
    pages         = IntegerField("Pages",      validators=[Optional(), NumberRange(min=1)])
    description   = TextAreaField("Description", validators=[Optional()])
    total_copies  = IntegerField("Total Copies", validators=[DataRequired(), NumberRange(min=1)])
    category_id   = SelectField("Category",   coerce=int, validators=[Optional()])
    cover_image   = FileField("Cover Image",  validators=[
                        Optional(),
                        FileAllowed(["png","jpg","jpeg","gif","webp"], "Images only!")
                    ])
    submit        = SubmitField("Save Book")

    def validate_isbn(self, field):
        from flask import request
        # On edit, exclude current book
        book_id = request.view_args.get("book_id")
        q = Book.query.filter_by(isbn=field.data, is_deleted=False)
        if book_id:
            q = q.filter(Book.id != int(book_id))
        if q.first():
            raise ValidationError("ISBN already exists.")


# ─────────────────────────────────────────────────────────────────────────────
# Category Form
# ─────────────────────────────────────────────────────────────────────────────

class CategoryForm(FlaskForm):
    name        = StringField("Name",        validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional()])
    color       = StringField("Color",       validators=[Optional(), Length(max=7)])
    icon        = StringField("FA Icon",     validators=[Optional(), Length(max=50)])
    submit      = SubmitField("Save Category")


# ─────────────────────────────────────────────────────────────────────────────
# Member / User Forms
# ─────────────────────────────────────────────────────────────────────────────

class MemberForm(FlaskForm):
    full_name     = StringField("Full Name",     validators=[DataRequired(), Length(max=120)])
    username      = StringField("Username",      validators=[DataRequired(), Length(min=3, max=80)])
    email         = EmailField("Email",          validators=[DataRequired(), Email()])
    password      = PasswordField("Password",    validators=[Optional(), Length(min=6)])
    role          = SelectField("Role",          choices=[
                        ("student",    "Student"),
                        ("librarian",  "Librarian"),
                        ("super_admin","Super Admin"),
                    ])
    phone         = StringField("Phone",         validators=[Optional(), Length(max=20)])
    address       = TextAreaField("Address",     validators=[Optional()])
    student_id    = StringField("Student ID",    validators=[Optional(), Length(max=50)])
    membership_id = StringField("Membership ID", validators=[Optional(), Length(max=50)])
    department    = StringField("Department",    validators=[Optional(), Length(max=100)])
    course        = StringField("Course",        validators=[Optional(), Length(max=100)])
    max_books     = IntegerField("Max Books",    validators=[Optional(), NumberRange(min=1, max=20)])
    is_active     = BooleanField("Active",       default=True)
    submit        = SubmitField("Save Member")


# ─────────────────────────────────────────────────────────────────────────────
# Issue / Return Forms
# ─────────────────────────────────────────────────────────────────────────────

class IssueForm(FlaskForm):
    member_isbn  = StringField("Member ID / Username",
                               validators=[DataRequired()])
    book_isbn    = StringField("Book ISBN / Title",
                               validators=[DataRequired()])
    notes        = TextAreaField("Notes", validators=[Optional()])
    submit       = SubmitField("Issue Book")


class ReturnForm(FlaskForm):
    issue_id     = HiddenField("Issue ID",  validators=[DataRequired()])
    return_notes = TextAreaField("Notes",   validators=[Optional()])
    mark_lost    = BooleanField("Mark as Lost")
    submit       = SubmitField("Return Book")


class RenewForm(FlaskForm):
    issue_id = HiddenField("Issue ID", validators=[DataRequired()])
    submit   = SubmitField("Renew")


# ─────────────────────────────────────────────────────────────────────────────
# Fine Forms
# ─────────────────────────────────────────────────────────────────────────────

class FinePaymentForm(FlaskForm):
    fine_id = HiddenField("Fine ID", validators=[DataRequired()])
    notes   = TextAreaField("Notes", validators=[Optional()])
    submit  = SubmitField("Mark as Paid")


class FineWaiveForm(FlaskForm):
    fine_id = HiddenField("Fine ID", validators=[DataRequired()])
    reason  = TextAreaField("Reason", validators=[DataRequired()])
    submit  = SubmitField("Waive Fine")


# ─────────────────────────────────────────────────────────────────────────────
# Settings Form
# ─────────────────────────────────────────────────────────────────────────────

class SettingsForm(FlaskForm):
    library_name        = StringField("Library Name",        validators=[DataRequired()])
    library_tagline     = StringField("Tagline",             validators=[Optional()])
    library_email       = EmailField("Library Email",        validators=[Optional(), Email()])
    library_phone       = StringField("Phone",               validators=[Optional()])
    library_address     = TextAreaField("Address",           validators=[Optional()])
    fine_per_day        = FloatField("Fine Per Day (₹)",     validators=[DataRequired(), NumberRange(min=0)])
    max_fine_limit      = FloatField("Max Fine Limit (₹)",   validators=[DataRequired(), NumberRange(min=0)])
    max_books_student   = IntegerField("Max Books/Student",  validators=[DataRequired(), NumberRange(min=1)])
    default_issue_days  = IntegerField("Default Issue Days", validators=[DataRequired(), NumberRange(min=1)])
    renew_days          = IntegerField("Renew Extension (days)", validators=[DataRequired(), NumberRange(min=1)])
    max_fine_block      = FloatField("Block Limit (₹)",      validators=[DataRequired(), NumberRange(min=0)])
    allow_registration  = BooleanField("Allow Public Registration")
    submit              = SubmitField("Save Settings")


# ─────────────────────────────────────────────────────────────────────────────
# Search Form (GET)
# ─────────────────────────────────────────────────────────────────────────────

class BookSearchForm(FlaskForm):
    class Meta:
        csrf = False   # GET form, no CSRF needed
    q          = StringField("Search",   validators=[Optional()])
    category   = SelectField("Category", coerce=int, validators=[Optional()])
    status     = SelectField("Status",   choices=[
                     ("", "All"), ("available", "Available"),
                     ("issued", "Issued"), ("lost", "Lost"), ("damaged", "Damaged")
                 ], validators=[Optional()])
    submit     = SubmitField("Search")
