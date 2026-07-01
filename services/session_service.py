"""Session Drop business logic."""

import os
import shutil
import sqlite3
from datetime import datetime

from services.file_service import save_uploaded_file
from utils.codes import (
    MAX_NOTE_LENGTH,
    generate_unique_session_codes,
    is_valid_session_code,
)


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _row_to_session(row):
    return {
        'id': row[0],
        'owner_code': row[1],
        'viewer_code': row[2],
        'session_name': row[3],
        'created_at': _parse_datetime(row[4]),
        'updated_at': _parse_datetime(row[5]),
        'is_active': bool(row[6]),
    }


def _row_to_file(row):
    return {
        'id': row[0],
        'session_id': row[1],
        'filename': row[2],
        'original_filename': row[3],
        'file_path': row[4],
        'file_size': row[5],
        'note': row[6] or '',
        'upload_order': row[7],
        'created_at': _parse_datetime(row[8]),
    }


def get_session_storage_path(storage_path, session_id):
    return os.path.join(storage_path, 'sessions', str(session_id))


def create_session(database_path, storage_path, session_name=None):
    """Create a new session with unique owner and viewer codes."""
    owner_code, viewer_code = generate_unique_session_codes(database_path)
    name = (session_name or '').strip() or None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO sessions (owner_code, viewer_code, session_name)
            VALUES (?, ?, ?)
            ''',
            (owner_code, viewer_code, name),
        )
        session_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    session_dir = get_session_storage_path(storage_path, session_id)
    os.makedirs(session_dir, exist_ok=True)

    return get_session_by_owner_code(database_path, owner_code)


def get_session_by_owner_code(database_path, owner_code):
    """Fetch active session by owner code."""
    if not is_valid_session_code(owner_code):
        return None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, owner_code, viewer_code, session_name, created_at, updated_at, is_active
        FROM sessions WHERE owner_code = ? AND is_active = 1
        ''',
        (owner_code.upper(),),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def get_session_by_viewer_code(database_path, viewer_code):
    """Fetch active session by viewer code."""
    if not is_valid_session_code(viewer_code):
        return None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, owner_code, viewer_code, session_name, created_at, updated_at, is_active
        FROM sessions WHERE viewer_code = ? AND is_active = 1
        ''',
        (viewer_code.upper(),),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def get_session_files(database_path, session_id):
    """Return session files ordered newest first (LIFO stack)."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, session_id, filename, original_filename, file_path, file_size, note,
               upload_order, created_at
        FROM session_files
        WHERE session_id = ?
        ORDER BY upload_order DESC
        ''',
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_file(row) for row in rows]


def get_session_file(database_path, file_id):
    """Fetch a single session file record."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, session_id, filename, original_filename, file_path, file_size, note,
               upload_order, created_at
        FROM session_files WHERE id = ?
        ''',
        (file_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_file(row) if row else None


def upload_session_file(database_path, storage_path, owner_code, file_storage, note=''):
    """Upload a file to an active session. Returns the new file record or raises ValueError."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        raise ValueError('Invalid or inactive owner code.')

    note = (note or '').strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(f'Note must be {MAX_NOTE_LENGTH} characters or fewer.')

    session_dir = get_session_storage_path(storage_path, session['id'])
    saved = save_uploaded_file(file_storage, session_dir)
    if not saved:
        raise ValueError('No valid file provided.')

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT COALESCE(MAX(upload_order), 0) + 1 FROM session_files WHERE session_id = ?',
            (session['id'],),
        )
        upload_order = cursor.fetchone()[0]

        cursor.execute(
            '''
            INSERT INTO session_files
            (session_id, filename, original_filename, file_path, file_size, note, upload_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                session['id'],
                saved['filename'],
                saved['original_filename'],
                saved['file_path'],
                saved['file_size'],
                note or None,
                upload_order,
            ),
        )
        file_id = cursor.lastrowid
        cursor.execute(
            'UPDATE sessions SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return get_session_file(database_path, file_id)


def delete_session_file(database_path, storage_path, owner_code, file_id):
    """Delete a file from a session. Returns True on success."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        return False

    file_record = get_session_file(database_path, file_id)
    if not file_record or file_record['session_id'] != session['id']:
        return False

    if os.path.exists(file_record['file_path']):
        try:
            os.remove(file_record['file_path'])
        except OSError:
            pass  # File may be locked or already removed

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM session_files WHERE id = ?', (file_id,))
        cursor.execute(
            'UPDATE sessions SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return True


def update_session_file_note(database_path, owner_code, file_id, note):
    """Update note on a session file."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        return None

    note = (note or '').strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(f'Note must be {MAX_NOTE_LENGTH} characters or fewer.')

    file_record = get_session_file(database_path, file_id)
    if not file_record or file_record['session_id'] != session['id']:
        return None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE session_files SET note = ? WHERE id = ?',
            (note or None, file_id),
        )
        cursor.execute(
            'UPDATE sessions SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return get_session_file(database_path, file_id)


def rename_session(database_path, owner_code, session_name):
    """Rename a session."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        return None

    name = (session_name or '').strip() or None
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE sessions SET session_name = ?, updated_at = ? WHERE id = ?',
            (name, datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return get_session_by_owner_code(database_path, owner_code)


def close_session(database_path, storage_path, owner_code):
    """Deactivate a session and remove its files from disk."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        return False

    session_dir = get_session_storage_path(storage_path, session['id'])
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM session_files WHERE session_id = ?', (session['id'],))
        cursor.execute(
            'UPDATE sessions SET is_active = 0, updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return True


def reorder_session_files(database_path, owner_code, file_ids):
    """Reorder files by assigning upload_order from highest to lowest for given ids."""
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        return False

    files = get_session_files(database_path, session['id'])
    existing_ids = {f['id'] for f in files}
    if set(file_ids) != existing_ids:
        return False

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        order = len(file_ids)
        for file_id in file_ids:
            cursor.execute(
                'UPDATE session_files SET upload_order = ? WHERE id = ? AND session_id = ?',
                (order, file_id, session['id']),
            )
            order -= 1
        cursor.execute(
            'UPDATE sessions SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), session['id']),
        )
        conn.commit()
    finally:
        conn.close()

    return True


def file_record_to_json(file_record):
    """Serialize a file record for JSON API responses."""
    return {
        'id': file_record['id'],
        'filename': file_record['filename'],
        'original_filename': file_record['original_filename'],
        'file_size': file_record['file_size'],
        'note': file_record['note'],
        'created_at': file_record['created_at'].isoformat() if file_record['created_at'] else None,
        'upload_order': file_record['upload_order'],
    }
