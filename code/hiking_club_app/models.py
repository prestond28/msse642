import sqlite3
from flask import g

DATABASE = 'hiking_club.db'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                -- role: "member" or "admin"
                -- real app would split admin into "trip_leader" and "system_admin"
                role TEXT NOT NULL DEFAULT 'member',
                name TEXT,
                emergency_contact TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trip_id INTEGER NOT NULL,
                UNIQUE(user_id, trip_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (trip_id) REFERENCES trips(id)
            );
        ''')
        db.commit()
        _seed_db(db)


def _seed_db(db):
    existing = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing > 0:
        return

    from werkzeug.security import generate_password_hash

    db.execute(
        'INSERT INTO users (username, email, password_hash, role, name) VALUES (?, ?, ?, ?, ?)',
        ('admin', 'admin@hikingclub.local', generate_password_hash('admin123'), 'admin', 'Club Admin')
    )
    db.execute(
        'INSERT INTO users (username, email, password_hash, role, name, emergency_contact) VALUES (?, ?, ?, ?, ?, ?)',
        ('jdoe', 'jdoe@example.com', generate_password_hash('member123'), 'member', 'Jane Doe', 'John Doe 555-1234')
    )
    db.execute(
        'INSERT INTO users (username, email, password_hash, role, name) VALUES (?, ?, ?, ?, ?)',
        ('bsmith', 'bsmith@example.com', generate_password_hash('member123'), 'member', 'Bob Smith')
    )

    db.execute(
        'INSERT INTO trips (name, date, description, created_by) VALUES (?, ?, ?, ?)',
        ('Mount Sanitas Loop', '2026-07-12', 'A moderate 3.1-mile loop with great views of Boulder. Meet at the trailhead at 8 AM.', 1)
    )
    db.execute(
        'INSERT INTO trips (name, date, description, created_by) VALUES (?, ?, ?, ?)',
        ('Rocky Mountain National Park Day Hike', '2026-07-26', 'Full-day hike to Emerald Lake via Bear Lake. Carpooling available from the clubhouse.', 1)
    )
    db.execute(
        'INSERT INTO trips (name, date, description, created_by) VALUES (?, ?, ?, ?)',
        ('Chautauqua Meadows Sunrise Walk', '2026-08-09', 'Easy 2-mile sunrise walk through Chautauqua Meadows. Beginners welcome!', 1)
    )

    db.commit()
