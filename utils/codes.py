"""Code generation utilities."""

import secrets
import sqlite3
from datetime import datetime

SESSION_CODE_LENGTH = 4
MAX_NOTE_LENGTH = 1000


def is_valid_session_code(code):
    """Return True if code is a valid 4-digit session code."""
    code = (code or '').strip()
    return len(code) == SESSION_CODE_LENGTH and code.isdigit()


def normalize_session_code(code):
    """Normalize and validate a session code, or return None."""
    code = (code or '').strip()
    if is_valid_session_code(code):
        return code
    return None


def _code_is_taken(cursor, code):
    """Check if a 4-digit code is used by an active drop or session."""
    cursor.execute(
        'SELECT 1 FROM drops WHERE code = ? AND expires_at > ? LIMIT 1',
        (code, datetime.now().isoformat()),
    )
    if cursor.fetchone():
        return True

    cursor.execute(
        '''
        SELECT 1 FROM sessions
        WHERE is_active = 1
          AND (expires_at IS NULL OR expires_at > ?)
          AND (owner_code = ? OR viewer_code = ?)
        LIMIT 1
        ''',
        (datetime.now().isoformat(), code, code),
    )
    return cursor.fetchone() is not None


def generate_unique_4_digit_code(database_path, exclude_codes=None, max_attempts=100):
    """Generate a unique 4-digit code not used by drops or sessions."""
    exclude_codes = exclude_codes or set()
    for _ in range(max_attempts):
        code = f'{secrets.randbelow(10000):04d}'
        if code in exclude_codes:
            continue

        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        try:
            if not _code_is_taken(cursor, code):
                return code
        finally:
            conn.close()

    raise RuntimeError('Unable to generate unique 4-digit code after maximum attempts')


def generate_unique_session_codes(database_path, max_attempts=100):
    """
    Generate a unique pair of 4-digit owner and viewer codes.
    Owner and viewer codes are always different.
    """
    for _ in range(max_attempts):
        owner_code = generate_unique_4_digit_code(database_path)
        try:
            viewer_code = generate_unique_4_digit_code(
                database_path,
                exclude_codes={owner_code},
            )
        except RuntimeError:
            continue
        if owner_code != viewer_code:
            return owner_code, viewer_code

    raise RuntimeError('Unable to generate unique session codes after maximum attempts')
