"""QR code routes for drops and sessions."""

from flask import Blueprint, abort, current_app, send_file, url_for

from utils.qr import generate_qr_png

qr_bp = Blueprint('qr', __name__)


def _send_qr(url):
    buffer = generate_qr_png(url)
    return send_file(buffer, mimetype='image/png', download_name='qr.png')


def _drop_exists(database_path, code):
    """Check if a drop code is valid and not expired."""
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM drops WHERE code = ? AND expires_at > ?',
        (code, datetime.now().isoformat()),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


@qr_bp.route('/qr/drop/<code>.png')
def drop_qr(code):
    """Generate QR code PNG for a normal drop."""
    if len(code) != 4 or not code.isdigit():
        abort(404)
    if not _drop_exists(current_app.config['DATABASE_PATH'], code):
        abort(404)

    url = url_for('view_drop', code=code, _external=True)
    return _send_qr(url)


@qr_bp.route('/qr/session/viewer/<viewer_code>.png')
def session_viewer_qr(viewer_code):
    """Generate QR code PNG for session viewer access."""
    from services.session_service import get_session_by_viewer_code

    session = get_session_by_viewer_code(current_app.config['DATABASE_PATH'], viewer_code)
    if not session:
        abort(404)

    url = url_for('session.view_session', viewer_code=session['viewer_code'], _external=True)
    return _send_qr(url)


@qr_bp.route('/qr/session/owner/<owner_code>.png')
def session_owner_qr(owner_code):
    """Generate QR code PNG for session owner management."""
    from services.session_service import get_session_by_owner_code

    session = get_session_by_owner_code(current_app.config['DATABASE_PATH'], owner_code)
    if not session:
        abort(404)

    url = url_for('session.manage_session', owner_code=session['owner_code'], _external=True)
    return _send_qr(url)
