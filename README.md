# Library Management System

A modern, robust, and professional Library Management System built with Python, Flask, SQLite, and Bootstrap 5.

## Features
- **Role-based Access Control**: Super Admin, Librarian, and Student roles with specific dashboards and permissions.
- **Book Management**: Full CRUD for books, categories. Support for soft-deletion and multiple copies.
- **Issue & Return**: Auto-calculates due dates and fines. Supports marking books as lost.
- **Member Management**: Track member history, fines, and maximum book borrowing limits.
- **Wishlist & Reservations**: Students can reserve books that are currently issued out.
- **Fines System**: Configurable daily fine amounts, limits, with options to pay or waive fines.
- **Reports & Analytics**: Visual charts on the dashboard and exportable CSV reports for issues and fines.
- **Modern UI/UX**: Clean layout using Bootstrap 5, Font Awesome icons, and custom styling.

## Prerequisites
- Python 3.8+
- pip

## Installation & Setup

1. **Clone the repository or navigate to the directory**:
   ```bash
   cd "Library Management System"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: ensure you are in a virtual environment if preferred)*

3. **Seed the database**:
   The `seed.py` script will create the database, tables, and populate it with sample users, categories, and books.
   ```bash
   python seed.py
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```
   Or use Flask CLI:
   ```bash
   flask run
   ```

5. **Access the web app**:
   Open your browser and navigate to `http://localhost:5000`

## Default Credentials (from seed.py)
- **Super Admin**: `admin` / `admin123`
- **Librarian**: `lib1` / `lib123`
- **Student**: `student1` / `student123`

## Project Structure
- `app.py`: Entry point and application factory.
- `models.py`: Database models (User, Book, Issue, Fine, etc.).
- `routes/`: Blueprint routing grouped by role (auth, admin, librarian, student, api).
- `templates/`: HTML templates using Jinja2, organized by role.
- `static/`: CSS, JS, and image uploads.
- `seed.py`: Database initialization script.
