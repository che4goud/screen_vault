"""
seed_user.py — Create a test user for local development.

Run once after init_db():
    python seed_user.py
"""

import uuid
from database import init_db, db

TEST_USER_ID = "dev-user-001"
TEST_USER_EMAIL = "dev@screenvault.local"

if __name__ == "__main__":
    init_db()
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, email, plan) VALUES (?, ?, 'pro')",
            (TEST_USER_ID, TEST_USER_EMAIL),
        )
    print(f"Test user ready:")
    print(f"  ID    : {TEST_USER_ID}")
    print(f"  Email : {TEST_USER_EMAIL}")
    print(f"\nSet in your shell:")
    print(f"  export SCREENVAULT_USER_ID={TEST_USER_ID}")
