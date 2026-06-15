import sqlite3
import pathlib

DB_PATH = pathlib.Path("data/tickets.db")


def init_ticket_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_by TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def create_ticket(title: str, description: str, priority: str, created_by: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO tickets (
            title,
            description,
            priority,
            created_by
        )
        VALUES (?, ?, ?, ?)
        ''',
        (
            title,
            description,
            priority,
            created_by
        )
    )

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return f"TICKET-{ticket_id:04d}"


def get_ticket(ticket_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    numeric_id = ticket_id.replace("TICKET-", "")

    cursor.execute(
        '''
        SELECT *
        FROM tickets
        WHERE id = ?
        ''',
        (numeric_id,)
    )

    ticket = cursor.fetchone()

    conn.close()

    if not ticket:
        return None

    ticket_data = dict(ticket)

    # expose human-friendly ticket ID
    ticket_data["ticket_id"] = f"TICKET-{ticket_data.pop('id'):04d}"

    return ticket_data