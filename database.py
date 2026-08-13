"""
database.py

This file sets up the SQLite database for the app. Run it on its own once
(python database.py) and it'll create a file called grocery_list.db with
all the tables
"""

# importing modules
import sqlite3

DB_NAME = "grocery_list.db"

def get_connection():
    # opens a connection to the database.
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    # calls get_connection() to open a connection to the database
    conn = get_connection()
    cursor = conn.cursor()

    # one row per person. doesn't know anything about households, a user could technically belong to more than one (handled in the next table).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    # one row per household. each household has a unique invite code that can be used to join it.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS households (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            invite_code TEXT NOT NULL UNIQUE
        )
    """)

    # this table is a many-to-many relationship between users and households. each row says "this user belongs to this household".
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS household_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            household_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (household_id) REFERENCES households (id)
        )
    """)

    # this table is for the grocery list items. each row is one item, and it belongs to a household. it also has a reference to the user who added it.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            household_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorised',
            added_by INTEGER NOT NULL,
            checked_off INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (household_id) REFERENCES households (id),
            FOREIGN KEY (added_by) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database ready: {DB_NAME}")

if __name__ == "__main__":
    create_tables()