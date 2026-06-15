import hashlib
import sqlite3
from helpdesk_agent.services.user_db import init_user_db, create_user
from helpdesk_agent.services.license_db import init_license_db, create_license
from helpdesk_agent.services.ticketing_service import init_ticket_db


def hash_password(password: str) -> str:
    """Create a SHA256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


def main():
    print("Seeding databases...")
    
    # Initialize schemas
    init_user_db()
    init_license_db()
    init_ticket_db()
    print("✓ Database schemas created")
    
    # Seed users
    users = [
        ("alice", "admin", hash_password("admin123")),
        ("bob", "employee", hash_password("bob123")),
        ("charlie", "employee", hash_password("charlie123")),
    ]
    
    for username, role, pwd_hash in users:
        try:
            create_user(username, role, pwd_hash)
            print(f"✓ Created user: {username} ({role})")
        except sqlite3.IntegrityError:
            print(f"  User {username} already exists")
        except Exception as e:
            print(f"  Error creating {username}: {e}")
    
    # Seed licenses
    licenses = [
        ("bob", "photoshop", "active"),
        ("bob", "slack", "expired"),
        ("alice", "photoshop", "active"),
        ("charlie", "slack", "trial"),
    ]
    
    for username, software, status in licenses:
        try:
            create_license(username, software, status)
            print(f"✓ Created license: {username} - {software} ({status})")
        except sqlite3.IntegrityError:
            print(f"  License {username}/{software} already exists")
        except Exception as e:
            print(f"  Error creating license: {e}")
    
    print("\n Database seeding complete!")
    print("\nTest credentials:")
    print("  Admin: alice / admin123")
    print("  Employee: bob / bob123")
    print("  Employee: charlie / charlie123")


if __name__ == "__main__":
    main()