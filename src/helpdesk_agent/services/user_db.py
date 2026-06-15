 # services/user_db.py

import sqlite3
import pathlib

DB_PATH = pathlib.Path("data/users.db")

# Role based access control
ROLE_PERMISSIONS = {
    "admin": [
        "reset_password",
        "view_license_status",
        "create_ticket"
    ],
    "employee": [
        "view_license_status",
        "create_ticket"
    ]
}


def init_user_db():
    """Initialize the users database with proper UNIQUE constraint on username."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            locked BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()


def get_user(username: str) -> dict | None:
    """Return user as dict, or None if not found."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def create_user(username: str, role: str, password_hash: str) -> None:
    """
    Create a new user in the database.
    
    Args:
        username: Unique username
        role: User role (admin, employee)
        password_hash: Hashed password
    
    Raises:
        sqlite3.IntegrityError: If username already exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (username, role, password_hash, locked)
        VALUES (?, ?, ?, 0)
    """, (username, role, password_hash))
    
    conn.commit()
    conn.close()


def reset_user_password(username: str, new_password_hash: str) -> None:
    """Update a user's password hash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (new_password_hash, username)
    )
    
    conn.commit()
    conn.close()


def user_has_permission(username: str, action: str) -> bool:
    """
    Check if a user has a specific permission based on their role.
    
    Args:
        username: The username to check
        action: The permission action (e.g., "reset_password", "view_license_status", "create_ticket")
    
    Returns:
        True if the user has the permission, False otherwise
    """
    user = get_user(username)
    
    if not user:
        return False
    
    if user.get("locked"):
        return False
    
    return action in ROLE_PERMISSIONS.get(user.get("role", ""), [])