"""Session Drop business logic."""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from services.file_service import save_uploaded_file
from utils.codes import (
    MAX_NOTE_LENGTH,
    generate_unique_session_codes,
    is_valid_session_code,
    normalize_session_code,
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
        'expires_at': _parse_datetime(row[7]) if len(row) > 7 else None,
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
        'item_type': row[9] if len(row) > 9 else 'file',
    }


def get_session_storage_path(storage_path, session_id):
    return os.path.join(storage_path, 'sessions', str(session_id))


def create_session(database_path, storage_path, session_name=None, expiry_hours=24):
    """Create a new session with unique owner and viewer codes."""
    owner_code, viewer_code = generate_unique_session_codes(database_path)
    name = (session_name or '').strip() or None
    expires_at = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO sessions (owner_code, viewer_code, session_name, expires_at)
            VALUES (?, ?, ?, ?)
            ''',
            (owner_code, viewer_code, name, expires_at),
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
    owner_code = normalize_session_code(owner_code)
    if not owner_code:
        return None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, owner_code, viewer_code, session_name, created_at, updated_at, is_active, expires_at
        FROM sessions
        WHERE owner_code = ? AND is_active = 1 AND expires_at > ?
        ''',
        (owner_code, datetime.now().isoformat()),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def get_session_by_viewer_code(database_path, viewer_code):
    """Fetch active session by viewer code."""
    viewer_code = normalize_session_code(viewer_code)
    if not viewer_code:
        return None

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, owner_code, viewer_code, session_name, created_at, updated_at, is_active, expires_at
        FROM sessions
        WHERE viewer_code = ? AND is_active = 1 AND expires_at > ?
        ''',
        (viewer_code, datetime.now().isoformat()),
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
               upload_order, created_at, item_type
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
               upload_order, created_at, item_type
        FROM session_files WHERE id = ?
        ''',
        (file_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_file(row) if row else None


def upload_session_file(database_path, storage_path, owner_code, file_storage, note=''):
    """
    Add a file and/or message to an active session.
    File is optional; a note/message alone creates a text drop in the session.
    """
    session = get_session_by_owner_code(database_path, owner_code)
    if not session:
        raise ValueError('Invalid or inactive owner code.')

    note = (note or '').strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(f'Note must be {MAX_NOTE_LENGTH} characters or fewer.')

    has_file = file_storage and file_storage.filename
    if not has_file and not note:
        raise ValueError('Please provide a file or a message.')

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT COALESCE(MAX(upload_order), 0) + 1 FROM session_files WHERE session_id = ?',
            (session['id'],),
        )
        upload_order = cursor.fetchone()[0]

        if has_file:
            session_dir = get_session_storage_path(storage_path, session['id'])
            saved = save_uploaded_file(file_storage, session_dir)
            if not saved:
                raise ValueError('No valid file provided.')

            cursor.execute(
                '''
                INSERT INTO session_files
                (session_id, filename, original_filename, file_path, file_size, note,
                 upload_order, item_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'file')
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
        else:
            cursor.execute(
                '''
                INSERT INTO session_files
                (session_id, filename, original_filename, file_path, file_size, note,
                 upload_order, item_type)
                VALUES (?, '', 'Message', '', 0, ?, ?, 'message')
                ''',
                (session['id'], note, upload_order),
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

    if file_record['item_type'] != 'message' and file_record['file_path']:
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


def cleanup_expired_sessions(database_path, storage_path):
    """Remove expired session drops and their files."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute(
        '''
        SELECT id FROM sessions
        WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?
        ''',
        (now,),
    )
    expired_ids = [row[0] for row in cursor.fetchall()]

    for session_id in expired_ids:
        session_dir = get_session_storage_path(storage_path, session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        cursor.execute('DELETE FROM session_files WHERE session_id = ?', (session_id,))
        cursor.execute(
            'UPDATE sessions SET is_active = 0, updated_at = ? WHERE id = ?',
            (now, session_id),
        )

    conn.commit()
    conn.close()


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
        'item_type': file_record.get('item_type', 'file'),
        'is_message': file_record.get('item_type') == 'message',
        'created_at': file_record['created_at'].isoformat() if file_record['created_at'] else None,
        'upload_order': file_record['upload_order'],
    }
