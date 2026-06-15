import sqlite3
import pathlib

DB_PATH = pathlib.Path("data/licenses.db")


def init_license_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            username TEXT NOT NULL,
            software_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'none',
            PRIMARY KEY (username, software_name)
        )
    ''')

    conn.commit()
    conn.close()


def get_license_status(username: str, software_name: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT status 
        FROM licenses 
        WHERE username = ? AND software_name = ?
        ''',
        (username, software_name)
    )

    license_row = cursor.fetchone()
    conn.close()

    if not license_row:
        return "none"

    return license_row[0]


def create_license(username: str, software_name: str, status: str) -> None:
    """
    Create a new license record for a user.
    
    Args:
        username: Username of the license holder
        software_name: Name of the software
        status: License status (active, expired, trial, none)
    
    Raises:
        sqlite3.IntegrityError: If license for this user/software already exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO licenses (username, software_name, status)
        VALUES (?, ?, ?)
    """, (username, software_name, status))
    
    conn.commit()
    conn.close()