"""
Automated functional verification test for CivicPulse
Verifies that all routes, authentication, voting, and status updates work as expected.
"""

from app import app
from database import init_db

def run_tests():
    print("[Testing] Initializing fresh test client...")
    init_db()
    client = app.test_client()

    # 1. Test Home / Feed Page
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200 for '/', got {res.status_code}"
    assert b"CivicPulse" in res.data, "CivicPulse brand missing in home page"
    assert b"Hazardous Deep Pothole" in res.data, "Seeded issue missing in home feed"
    print("  [PASS] Public feed loads successfully with seeded issues.")

    # 2. Test Single Issue Detail Page
    res = client.get("/issue/1")
    assert res.status_code == 200, f"Expected 200 for '/issue/1', got {res.status_code}"
    assert b"Outer Ring Road" in res.data
    assert b"Discussion & Official Updates" in res.data
    print("  [PASS] Issue detail page loads with map and comments.")

    # 3. Test Citizen Login
    login_res = client.post("/login", data={
        "username": "citizen",
        "password": "citizen123"
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Welcome back" in login_res.data
    print("  [PASS] Citizen login functions correctly.")

    # 4. Test Upvote System (one vote per user)
    # Check issue 2 (not yet upvoted by citizen)
    upvote_res = client.post("/issue/2/upvote", follow_redirects=True)
    assert upvote_res.status_code == 200
    assert b"Thank you for endorsing this issue" in upvote_res.data
    print("  [PASS] Citizen can upvote an issue.")

    # Toggle upvote again
    upvote_toggle = client.post("/issue/2/upvote", follow_redirects=True)
    assert upvote_toggle.status_code == 200
    assert b"Your upvote was removed" in upvote_toggle.data
    print("  [PASS] Upvote toggle/undo works accurately.")

    # 5. Test Adding a Comment
    comment_res = client.post("/issue/1/comment", data={
        "comment_text": "This is a verified test comment from automated test."
    }, follow_redirects=True)
    assert comment_res.status_code == 200
    assert b"Comment posted successfully" in comment_res.data
    assert b"This is a verified test comment" in comment_res.data
    print("  [PASS] Posting comments works.")

    # 6. Test Admin Role Protection
    # Currently logged in as citizen, should be blocked from /admin
    admin_blocked = client.get("/admin", follow_redirects=True)
    assert b"Access denied: Administrator privileges required" in admin_blocked.data
    print("  [PASS] Role-based access control blocks citizen from admin dashboard.")

    # 7. Test Admin Login and Status Update
    client.get("/logout")
    admin_login = client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    }, follow_redirects=True)
    assert admin_login.status_code == 200
    assert b"Admin Management Portal" in admin_login.data
    print("  [PASS] Admin login redirects to admin dashboard.")

    # Change issue status to 'Resolved'
    status_update = client.post("/admin/issue/2/status", data={
        "status": "Resolved",
        "admin_note": "Electrician team replaced faulty wiring and bulbs."
    }, follow_redirects=True)
    assert status_update.status_code == 200
    assert b"status updated to" in status_update.data and b"Resolved" in status_update.data
    print("  [PASS] Admin status update works and posts official note.")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! The application is fully working. <<<")

if __name__ == "__main__":
    run_tests()
