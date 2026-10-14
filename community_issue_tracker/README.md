# CivicPulse - Community Issue Reporting Platform (PS 04)

A clean, dark-themed civic issue tracking website built in Python using **Flask**, **SQLite**, and **Leaflet.js**. 

This platform connects citizens with municipal administrators so that local issues (potholes, dark streetlights, garbage overflow, broken drains) can be reported, publicly upvoted, and systematically tracked until resolution.

---

## 🚀 How to Run the Website

### Step 1: Install Flask (if not already installed)
```bash
pip install flask pillow
```

### Step 2: Run the Application
Open your terminal in this directory and run:
```bash
python app.py
```

### Step 3: Open in Your Browser
Visit:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Login Accounts

Pre-seeded accounts are ready to use right away:

| Role | Username | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Municipal Admin** | `admin` | `admin123` | Update issue statuses, delete spam, post official resolution notes |
| **Citizen** | `citizen` | `citizen123` | Report new civic issues, upload photos, upvote once, write comments |
| **Citizen 2** | `priya` | `priya123` | Second citizen account to test upvote & discussion features |

*Tip: The login page includes 1-click **"Fill Demo"** buttons for quick testing during demonstrations!*

---

## 🛠️ How You Can Edit and Customize

This project is written to be easy to read and modify:

### 1. Change Categories
Open `app.py` and modify the `CATEGORIES` list:
```python
CATEGORIES = [
    "Roads & Potholes",
    "Streetlights & Electricity",
    "Garbage & Sanitation",
    "Water & Drainage",
    "Public Transport & Traffic",
    "Parks & Environment",
    "Other Civic Issue"
]
```

### 2. Change Dark Theme Colors
Open `static/css/style.css`. The entire color scheme is defined at the very top under `:root`:
```css
:root {
  --bg-main: #0d1117;       /* Main page background */
  --bg-card: #161b22;       /* Cards and tables */
  --border-color: #30363d;  /* Borders */
  --primary-btn: #238636;   /* Button green accent */
  --accent-btn: #1f6feb;    /* Button blue accent */
}
```

### 3. Change Default City / Map Center
Open `templates/report.html` and change the default coordinates (currently set to Bangalore center `12.9716, 77.5946`):
```javascript
let defaultLat = 12.9716;
let defaultLng = 77.5946;
```

---

## 📂 Project Structure

```text
community_issue_tracker/
├── app.py                   # Main Flask backend (routes, auth, voting logic)
├── database.py              # SQLite database schema, initialization & seed data
├── database.db              # SQLite database file (auto-generated on first run)
├── static/
│   ├── css/
│   │   └── style.css        # Clean dark theme stylesheet (customizable variables)
│   └── uploads/             # Stores uploaded issue photos
└── templates/
    ├── base.html            # Dark navbar, flash alerts, and layout shell
    ├── index.html           # Public feed, search, filter chips, upvote cards
    ├── report.html          # Issue submission form with interactive GPS map picker
    ├── issue_detail.html    # Full issue page with Leaflet map, comments, and upvote toggle
    ├── admin_dashboard.html # Admin dashboard with status management table
    ├── login.html           # Login page with demo autofill buttons
    └── register.html        # Account creation for citizens and officials
```

---

## ✨ Features Implemented (from Problem Statement 04)

- **Issue Submission Form**: Title, Category, Location, Detailed Description, Photo upload, and GPS coordinates.
- **Public Feed**: Filterable by category and status, searchable, and sortable by newest or most upvoted.
- **Strict Upvote Rule**: Citizens can endorse each issue exactly once (stored in database with unique constraint `(user_id, issue_id)`).
- **Admin Dashboard**: Role-protected dashboard for municipal authorities to update statuses (`Pending`, `In Progress`, `Resolved`) and delete issues.
- **Role-Based Access Control**: Decorators `@login_required` and `@admin_required` protect unauthorized access.
- **Map Integration**: Free, lightweight Leaflet.js with dark-mode map tiles to view and pick issue locations.
- **Comments Section**: Community discussions and official municipal updates for each issue.
- **Image Uploads**: Upload photo proof stored locally with collision-free unique filenames.
