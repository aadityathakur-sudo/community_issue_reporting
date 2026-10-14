"""
CivicPulse - Community Issue Reporting Platform (PS 04)
A student-built web application to report, upvote, and track local civic issues.
Tech Stack: Python, Flask, SQLite, Jinja2, Leaflet.js, Custom Dark Theme CSS.
"""

import os
import uuid
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db

app = Flask(__name__)
# Secret key for sessions & flash messages (easy to edit)
app.secret_key = "civicpulse-secret-key-student-project"

# Configuration for file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # Max 5MB upload

# Pre-defined civic issue categories (easy to edit or add new ones)
CATEGORIES = [
    "Roads & Potholes",
    "Streetlights & Electricity",
    "Garbage & Sanitation",
    "Water & Drainage",
    "Public Transport & Traffic",
    "Parks & Environment",
    "Other Civic Issue"
]

STATUS_CHOICES = ["Pending", "In Progress", "Resolved"]


def allowed_file(filename):
    """Check if the uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    """Decorator to protect routes requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to perform this action.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to protect admin-only routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_globals():
    """Make categories and current session details available to all templates."""
    return {
        "CATEGORIES": CATEGORIES,
        "STATUS_CHOICES": STATUS_CHOICES,
        "is_logged_in": "user_id" in session,
        "current_username": session.get("username"),
        "current_fullname": session.get("full_name"),
        "current_role": session.get("role")
    }


# ==============================================================================
# CITIZEN & PUBLIC FEED ROUTES
# ==============================================================================

@app.route("/")
def index():
    """
    Public feed of issues.
    Supports filtering by category, search query, and sorting by recency or upvotes.
    """
    category_filter = request.args.get("category", "").strip()
    sort_by = request.args.get("sort", "recent")  # 'recent' or 'upvotes'
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    # Base query joining issues with users to get reporter full name
    query = """
        SELECT issues.*, users.full_name AS reporter_name,
               (SELECT COUNT(*) FROM comments WHERE comments.issue_id = issues.id) AS comment_count
        FROM issues
        JOIN users ON issues.user_id = users.id
        WHERE 1=1
    """
    params = []

    if category_filter:
        query += " AND issues.category = ?"
        params.append(category_filter)

    if status_filter:
        query += " AND issues.status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (issues.title LIKE ? OR issues.description LIKE ? OR issues.location LIKE ?)"
        like_pattern = f"%{search_query}%"
        params.extend([like_pattern, like_pattern, like_pattern])

    if sort_by == "upvotes":
        query += " ORDER BY issues.upvotes DESC, issues.created_at DESC"
    else:
        query += " ORDER BY issues.created_at DESC"

    cursor.execute(query, params)
    issues = cursor.fetchall()

    # Get community stats for header counters
    cursor.execute("SELECT COUNT(*) FROM issues")
    total_issues = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Pending'")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Resolved'")
    resolved_count = cursor.fetchone()[0]

    # Check which issues the logged-in user has already upvoted
    user_upvoted_ids = set()
    if "user_id" in session:
        cursor.execute("SELECT issue_id FROM upvotes WHERE user_id = ?", (session["user_id"],))
        user_upvoted_ids = {row["issue_id"] for row in cursor.fetchall()}

    conn.close()

    return render_template(
        "index.html",
        issues=issues,
        category_filter=category_filter,
        sort_by=sort_by,
        search_query=search_query,
        status_filter=status_filter,
        total_issues=total_issues,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        user_upvoted_ids=user_upvoted_ids
    )


@app.route("/issue/<int:issue_id>")
def issue_detail(issue_id):
    """View details of a single issue, its location map, upvotes, and comments."""
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the issue details with the author's info
    cursor.execute("""
        SELECT issues.*, users.full_name AS reporter_name, users.username AS reporter_username
        FROM issues
        JOIN users ON issues.user_id = users.id
        WHERE issues.id = ?
    """, (issue_id,))
    issue = cursor.fetchone()

    if not issue:
        conn.close()
        flash("The requested issue could not be found.", "danger")
        return redirect(url_for("index"))

    # Fetch all comments for this issue
    cursor.execute("""
        SELECT comments.*, users.full_name AS author_name, users.role AS author_role
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.issue_id = ?
        ORDER BY comments.created_at ASC
    """, (issue_id,))
    comments = cursor.fetchall()

    # Check if the current user has already upvoted this issue
    has_upvoted = False
    if "user_id" in session:
        cursor.execute("""
            SELECT 1 FROM upvotes WHERE user_id = ? AND issue_id = ?
        """, (session["user_id"], issue_id))
        has_upvoted = cursor.fetchone() is not None

    conn.close()

    return render_template(
        "issue_detail.html",
        issue=issue,
        comments=comments,
        has_upvoted=has_upvoted
    )


@app.route("/report", methods=["GET", "POST"])
@login_required
def report_issue():
    """Form to submit a new civic issue report with image and GPS coordinates."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        
        # Coordinates from the interactive map picker
        latitude_str = request.form.get("latitude", "").strip()
        longitude_str = request.form.get("longitude", "").strip()

        # Input validation
        if not title or not description or not category or not location:
            flash("Please fill out all required fields (Title, Category, Location, Description).", "danger")
            return render_template("report.html", form=request.form)

        # Parse coordinates (defaulting to Bangalore/City center if omitted)
        try:
            latitude = float(latitude_str) if latitude_str else 12.9716
            longitude = float(longitude_str) if longitude_str else 77.5946
        except ValueError:
            latitude = 12.9716
            longitude = 77.5946

        # Handle image upload
        image_filename = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename != "" and allowed_file(file.filename):
                safe_name = secure_filename(file.filename)
                # Prefix with unique UUID to prevent overwriting files with the same name
                unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                file.save(file_path)
                image_filename = unique_name

        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO issues (title, description, category, location, latitude, longitude, image_filename, status, upvotes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', 0, ?)
        """, (title, description, category, location, latitude, longitude, image_filename, session["user_id"]))
        new_issue_id = cursor.lastrowid
        conn.commit()
        conn.close()

        flash("Your issue has been reported successfully! Local authorities have been notified.", "success")
        return redirect(url_for("issue_detail", issue_id=new_issue_id))

    return render_template("report.html")


@app.route("/issue/<int:issue_id>/upvote", methods=["POST"])
def upvote_issue(issue_id):
    """
    Upvote an issue.
    Enforces the rule that a citizen can endorse an issue exactly once.
    """
    if "user_id" not in session:
        # If not logged in, prompt user
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Please log in to upvote issues."}), 401
        flash("Please log in to endorse/upvote issues.", "warning")
        return redirect(url_for("login", next=url_for("issue_detail", issue_id=issue_id)))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()

    # Check if already upvoted
    cursor.execute("SELECT id FROM upvotes WHERE user_id = ? AND issue_id = ?", (user_id, issue_id))
    existing_vote = cursor.fetchone()

    if existing_vote:
        # Citizen already upvoted: toggle it off (remove endorsement) or alert
        cursor.execute("DELETE FROM upvotes WHERE user_id = ? AND issue_id = ?", (user_id, issue_id))
        cursor.execute("UPDATE issues SET upvotes = MAX(0, upvotes - 1) WHERE id = ?", (issue_id,))
        conn.commit()
        
        # Get updated count
        cursor.execute("SELECT upvotes FROM issues WHERE id = ?", (issue_id,))
        new_count = cursor.fetchone()[0]
        conn.close()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "action": "removed", "new_count": new_count})
        flash("Your upvote was removed.", "info")
    else:
        # Add new upvote
        cursor.execute("INSERT INTO upvotes (user_id, issue_id) VALUES (?, ?)", (user_id, issue_id))
        cursor.execute("UPDATE issues SET upvotes = upvotes + 1 WHERE id = ?", (issue_id,))
        conn.commit()

        # Get updated count
        cursor.execute("SELECT upvotes FROM issues WHERE id = ?", (issue_id,))
        new_count = cursor.fetchone()[0]
        conn.close()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "action": "added", "new_count": new_count})
        flash("Thank you for endorsing this issue!", "success")

    return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))


@app.route("/issue/<int:issue_id>/comment", methods=["POST"])
@login_required
def add_comment(issue_id):
    """Add a discussion comment or official municipal update to an issue."""
    comment_text = request.form.get("comment_text", "").strip()

    if not comment_text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for("issue_detail", issue_id=issue_id))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (issue_id, user_id, comment_text)
        VALUES (?, ?, ?)
    """, (issue_id, session["user_id"], comment_text))
    conn.commit()
    conn.close()

    flash("Comment posted successfully.", "success")
    return redirect(url_for("issue_detail", issue_id=issue_id))


# ==============================================================================
# ADMIN MANAGEMENT DASHBOARD & ROLE-BASED ACCESS CONTROL
# ==============================================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Administrator dashboard to view all civic reports,
    manage statuses (Pending, In Progress, Resolved), and monitor community feedback.
    """
    status_filter = request.args.get("status", "")
    category_filter = request.args.get("category", "")
    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT issues.*, users.full_name AS reporter_name, users.username AS reporter_username
        FROM issues
        JOIN users ON issues.user_id = users.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND issues.status = ?"
        params.append(status_filter)

    if category_filter:
        query += " AND issues.category = ?"
        params.append(category_filter)

    if search:
        query += " AND (issues.title LIKE ? OR issues.location LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY issues.created_at DESC"

    cursor.execute(query, params)
    issues = cursor.fetchall()

    # Overview statistics
    cursor.execute("SELECT COUNT(*) FROM issues")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Pending'")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'Resolved'")
    resolved_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        issues=issues,
        total_count=total_count,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        status_filter=status_filter,
        category_filter=category_filter,
        search=search
    )


@app.route("/admin/issue/<int:issue_id>/status", methods=["POST"])
@admin_required
def update_status(issue_id):
    """Admin action: update issue status and optionally append an official comment."""
    new_status = request.form.get("status", "").strip()
    admin_note = request.form.get("admin_note", "").strip()

    if new_status not in STATUS_CHOICES:
        flash("Invalid status selected.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE issues SET status = ? WHERE id = ?", (new_status, issue_id))

    # If the administrator wrote a note, post it as an official comment
    if admin_note:
        cursor.execute("""
            INSERT INTO comments (issue_id, user_id, comment_text)
            VALUES (?, ?, ?)
        """, (issue_id, session["user_id"], f"[Status changed to '{new_status}'] {admin_note}"))

    conn.commit()
    conn.close()

    flash(f"Issue #{issue_id} status updated to '{new_status}'.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin/issue/<int:issue_id>/delete", methods=["POST"])
@admin_required
def delete_issue(issue_id):
    """Admin action: delete an invalid or spam issue."""
    conn = get_db()
    cursor = conn.cursor()

    # Check for image file to delete from disk
    cursor.execute("SELECT image_filename FROM issues WHERE id = ?", (issue_id,))
    row = cursor.fetchone()
    if row and row["image_filename"]:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], row["image_filename"])
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    cursor.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()

    flash(f"Issue #{issue_id} has been permanently deleted.", "info")
    return redirect(url_for("admin_dashboard"))


# ==============================================================================
# AUTHENTICATION: LOGIN, REGISTER & LOGOUT
# ==============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in as Citizen or Municipal Authority/Admin."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            flash(f"Welcome back, {user['full_name']}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new citizen account."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        role = request.form.get("role", "citizen").strip()  # default citizen

        if role not in ["citizen", "admin"]:
            role = "citizen"

        if not username or not full_name or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            flash("Username already exists. Please choose another.", "warning")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, full_name, role))
        conn.commit()
        conn.close()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    """Log out of the current session."""
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("index"))


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    # Ensure database tables exist and sample data is seeded
    init_db()

    # Ensure uploads directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    print("==================================================")
    print("  CivicPulse - Community Issue Reporting Platform ")
    print("  Status: Server starting...")
    print("  URL: http://127.0.0.1:5000")
    print("  Default Admin Login:   admin / admin123")
    print("  Default Citizen Login: citizen / citizen123")
    print("==================================================")

    # Run local development server
    app.run(debug=True, host="127.0.0.1", port=5000)
