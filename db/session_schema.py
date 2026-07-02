"""Session Drop database schema (additive only — does not modify drops/files)."""


def init_session_tables(cursor):
    """Create session-related tables and indexes if they do not exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_code TEXT UNIQUE NOT NULL,
            viewer_code TEXT UNIQUE NOT NULL,
            session_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            expires_at TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            note TEXT,
            upload_order INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions (owner_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_viewer ON sessions (viewer_code)')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_files_session ON session_files (session_id)'
    )
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_session_files_order ON session_files (session_id, upload_order DESC)'
    )

    _migrate_session_tables(cursor)


def _migrate_session_tables(cursor):
    """Apply additive schema updates for existing databases."""
    cursor.execute('PRAGMA table_info(session_files)')
    columns = {row[1] for row in cursor.fetchall()}
    if 'item_type' not in columns:
        cursor.execute(
            "ALTER TABLE session_files ADD COLUMN item_type TEXT DEFAULT 'file'"
        )

    cursor.execute('PRAGMA table_info(sessions)')
    session_columns = {row[1] for row in cursor.fetchall()}
    if 'expires_at' not in session_columns:
        cursor.execute('ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP')
        cursor.execute(
            '''
            UPDATE sessions
            SET expires_at = datetime(created_at, '+24 hours')
            WHERE expires_at IS NULL
            '''
        )
