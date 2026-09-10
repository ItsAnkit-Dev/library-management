"""
Configuration module for the Library Management System.
Defines different config classes for development, testing, and production.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "lms-super-secret-key-change-in-production-2024")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevent CSRF token from expiring while the session is active

    # ── Database ───────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "library.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Session ────────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ── File Upload ────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "covers")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # ── Library Business Rules (editable via Settings page) ───────────────────
    FINE_PER_DAY = 2.00           # ₹ per day overdue
    MAX_FINE_LIMIT = 200.00       # ₹ max fine per book
    MAX_BOOKS_PER_STUDENT = 3     # how many books a student can hold
    DEFAULT_ISSUE_DAYS = 14       # default borrow period
    RENEW_EXTENSION_DAYS = 7      # days added on renewal
    MAX_FINE_BEFORE_BLOCK = 50.00 # block issuing if unpaid fine exceeds this
    ALLOW_REGISTRATION = True     # toggle public registration

    # ── Library Info ──────────────────────────────────────────────────────────
    LIBRARY_NAME = "Modern Library"
    LIBRARY_TAGLINE = "Knowledge is Power"
    LIBRARY_EMAIL = "library@example.com"
    LIBRARY_PHONE = "+91-9876543210"
    LIBRARY_ADDRESS = "123 Book Street, Knowledge City"


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing-specific configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Map string name → class (used in app.py)
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
