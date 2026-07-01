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
            is_active INTEGER DEFAULT 1
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
