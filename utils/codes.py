"""Code generation utilities."""

import secrets
import sqlite3
import string
from datetime import datetime

# Session codes use a distinct alphabet (no ambiguous 0/O, 1/I/L).
SESSION_CODE_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
SESSION_CODE_LENGTH = 16
MAX_NOTE_LENGTH = 1000


def generate_session_code():
    """Generate a cryptographically secure session code (not 4-digit)."""
    return ''.join(secrets.choice(SESSION_CODE_ALPHABET) for _ in range(SESSION_CODE_LENGTH))


def is_valid_session_code(code):
    """Return True if code matches session code format."""
    if not code or len(code) != SESSION_CODE_LENGTH:
        return False
    return all(c in SESSION_CODE_ALPHABET for c in code.upper())


def generate_unique_session_codes(database_path, max_attempts=100):
    """
    Generate a unique pair of owner and viewer codes.
    Ensures neither collides with existing session codes or active drop codes.
    """
    for _ in range(max_attempts):
        owner_code = generate_session_code()
        viewer_code = generate_session_code()
        if owner_code == viewer_code:
            continue

        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                SELECT 1 FROM sessions
                WHERE owner_code IN (?, ?) OR viewer_code IN (?, ?)
                LIMIT 1
                ''',
                (owner_code, viewer_code, owner_code, viewer_code),
            )
            if cursor.fetchone():
                continue

            # Avoid collision with active (non-expired) drop codes (4-digit only).
            cursor.execute(
                '''
                SELECT 1 FROM drops
                WHERE code IN (?, ?) AND expires_at > ?
                LIMIT 1
                ''',
                (owner_code, viewer_code, datetime.now().isoformat()),
            )
            if cursor.fetchone():
                continue

            return owner_code, viewer_code
        finally:
            conn.close()

    raise RuntimeError('Unable to generate unique session codes after maximum attempts')
