"""
database.py - Database setup and helpers
Community Issue Reporting Platform
Author: Student Project
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

# Path to the SQLite database file
DB_NAME = os.path.join(os.path.dirname(__file__), "database.db")


def get_db():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name like dict: row['title']
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initializes tables and populates with realistic sample data if empty."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table (Citizens and Admins)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'citizen', -- 'citizen' or 'admin'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Issues Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        image_filename TEXT,
        status TEXT NOT NULL DEFAULT 'Pending', -- 'Pending', 'In Progress', 'Resolved'
        upvotes INTEGER NOT NULL DEFAULT 0,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 3. Upvotes Table (Ensures a user can upvote each issue only once)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upvotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        issue_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, issue_id),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (issue_id) REFERENCES issues (id) ON DELETE CASCADE
    );
    """)

    # 4. Comments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (issue_id) REFERENCES issues (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()

    # Check if we already have users; if not, seed initial data
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        print("[Database] First run detected. Seeding initial users and civic issues...")

        # Add Admin account and Citizen account
        # Passwords:
        #   admin -> admin123
        #   citizen -> citizen123
        #   priya -> priya123
        admin_pass = generate_password_hash("admin123")
        citizen_pass = generate_password_hash("citizen123")
        priya_pass = generate_password_hash("priya123")

        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ("admin", admin_pass, "Civic Administrator", "admin"))
        admin_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ("citizen", citizen_pass, "Rahul Sharma", "citizen"))
        citizen_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ("priya", priya_pass, "Priya Patel", "citizen"))
        priya_id = cursor.lastrowid

        # Seed sample civic issues
        seed_issues = [
            (
                "Hazardous Deep Pothole on Main Road near Metro Gate 2",
                "A large 2-foot waterlogged crater has formed right on the bus lane. Multiple scooter riders have slipped during rain. Urgently needs asphalt patching before heavy monsoon.",
                "Roads & Potholes",
                "Outer Ring Road, Near Metro Station Gate 2",
                12.9716,
                77.5946,
                "pothole_sample.jpg",
                "In Progress",
                14,
                citizen_id
            ),
            (
                "Streetlights Non-Functional on 4th Cross Avenue",
                "Four consecutive streetlights have been completely dark for over a week. The street is pitch black after 7 PM, creating safety concerns for women and elderly walking home.",
                "Streetlights & Electricity",
                "4th Cross, Gandhi Nagar, Sector 3",
                12.9780,
                77.6010,
                "streetlight_sample.jpg",
                "Pending",
                9,
                priya_id
            ),
            (
                "Overflowing Community Garbage Dump near Public School",
                "Garbage container has not been cleared for 5 days. Waste is spilling onto the road and stray animals are scattering plastic. Strong odor affecting nearby students.",
                "Garbage & Sanitation",
                "Opposite St. Xavier School, Ward 12",
                12.9650,
                77.5890,
                "garbage_sample.jpg",
                "Pending",
                21,
                citizen_id
            ),
            (
                "Broken Concrete Drainage Cover on Footpath",
                "The storm drainage slab cracked and collapsed into the canal. Pedestrians can fall inside at night. Temporary tree branch placed by shopkeepers as warning.",
                "Water & Drainage",
                "Market Junction, Next to Central Pharmacy",
                12.9820,
                77.5850,
                "drainage_sample.jpg",
                "Resolved",
                35,
                priya_id
            )
        ]

        cursor.executemany("""
            INSERT INTO issues (title, description, category, location, latitude, longitude, image_filename, status, upvotes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_issues)

        # Seed initial comments
        seed_comments = [
            (1, priya_id, 'I commute through here every day. It got significantly worse after yesterday rain!'),
            (1, admin_id, 'Road Maintenance team has been notified. Work order #RM-442 issued.'),
            (2, citizen_id, 'Reported to local BESCOM engineer as well. Hope it gets fixed soon.'),
            (3, priya_id, 'The municipal truck missed this street during regular pickup on Tuesday.'),
            (4, admin_id, 'Resolution update: Heavy-duty reinforced slab has been installed. Issue marked as Resolved.')
        ]
        cursor.executemany("""
            INSERT INTO comments (issue_id, user_id, comment_text)
            VALUES (?, ?, ?)
        """, seed_comments)

        # Seed upvote history so the demo users already upvoted
        cursor.execute("""
            INSERT INTO upvotes (user_id, issue_id)
            VALUES
            (?, 1), (?, 3), (?, 4)
        """, (citizen_id, citizen_id, citizen_id))

        conn.commit()
        print("[Database] Initial data seeded successfully!")

    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialization complete.")
