"""Session Drop routes and API endpoints."""

import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from services.file_service import format_file_size
from services.session_service import (
    close_session,
    delete_session_file,
    file_record_to_json,
    get_session_by_owner_code,
    get_session_by_viewer_code,
    get_session_file,
    get_session_files,
    create_session,
    rename_session,
    reorder_session_files,
    update_session_file_note,
    upload_session_file,
)
from utils.codes import is_valid_session_code, MAX_NOTE_LENGTH

session_bp = Blueprint('session', __name__)


def _db_path():
    return current_app.config['DATABASE_PATH']


def _storage_path():
    return current_app.config['STORAGE_PATH']


@session_bp.route('/session/create', methods=['POST'])
def create():
    """Create a new session drop."""
    session_name = request.form.get('session_name', '').strip()
    try:
        session = create_session(_db_path(), _storage_path(), session_name)
        return render_template(
            'session_created.html',
            session=session,
        )
    except Exception as exc:
        current_app.logger.error(f'Error creating session: {exc}')
        flash('An error occurred while creating the session.', 'error')
        return redirect(url_for('home'))


@session_bp.route('/session/manage/<owner_code>')
def manage_session(owner_code):
    """Owner dashboard for managing a session."""
    owner_code = owner_code.upper()
    if not is_valid_session_code(owner_code):
        return render_template('session_not_found.html', code=owner_code, role='owner')

    session = get_session_by_owner_code(_db_path(), owner_code)
    if not session:
        return render_template('session_not_found.html', code=owner_code, role='owner')

    files = get_session_files(_db_path(), session['id'])
    return render_template(
        'session_manage.html',
        session=session,
        files=files,
        max_note_length=MAX_NOTE_LENGTH,
        format_file_size=format_file_size,
    )


@session_bp.route('/session/view/<viewer_code>')
def view_session(viewer_code):
    """Read-only viewer page for a session."""
    viewer_code = viewer_code.upper()
    if not is_valid_session_code(viewer_code):
        return render_template('session_not_found.html', code=viewer_code, role='viewer')

    session = get_session_by_viewer_code(_db_path(), viewer_code)
    if not session:
        return render_template('session_not_found.html', code=viewer_code, role='viewer')

    files = get_session_files(_db_path(), session['id'])
    return render_template(
        'session_view.html',
        session=session,
        files=files,
        format_file_size=format_file_size,
    )


@session_bp.route('/session/open-viewer', methods=['POST'])
def open_viewer():
    """Redirect to session viewer from home page."""
    code = request.form.get('viewer_code', '').strip().upper()
    if not is_valid_session_code(code):
        flash('Please enter a valid session viewer code.', 'error')
        return redirect(url_for('home'))
    return redirect(url_for('session.view_session', viewer_code=code))


@session_bp.route('/session/open-owner', methods=['POST'])
def open_owner():
    """Redirect to session owner dashboard from home page."""
    code = request.form.get('owner_code', '').strip().upper()
    if not is_valid_session_code(code):
        flash('Please enter a valid session owner code.', 'error')
        return redirect(url_for('home'))
    return redirect(url_for('session.manage_session', owner_code=code))


@session_bp.route('/api/session/upload/<owner_code>', methods=['POST'])
def api_upload(owner_code):
    """Async file upload for session owner."""
    owner_code = owner_code.upper()
    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    file_storage = request.files.get('file')
    note = request.form.get('note', '')

    try:
        file_record = upload_session_file(
            _db_path(), _storage_path(), owner_code, file_storage, note
        )
        return jsonify({'ok': True, 'file': file_record_to_json(file_record)})
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.error(f'Session upload error: {exc}')
        return jsonify({'ok': False, 'error': 'Upload failed. Please try again.'}), 500


@session_bp.route('/api/session/file/<int:file_id>', methods=['DELETE'])
def api_delete_file(file_id):
    """Delete a session file (owner only)."""
    data = request.get_json(silent=True) or {}
    owner_code = (data.get('owner_code') or request.form.get('owner_code') or '').strip().upper()

    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    if delete_session_file(_db_path(), _storage_path(), owner_code, file_id):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'File not found or access denied.'}), 404


@session_bp.route('/api/session/file/<int:file_id>/note', methods=['PATCH'])
def api_update_note(file_id):
    """Update note on a session file (owner only)."""
    data = request.get_json(silent=True) or {}
    owner_code = (data.get('owner_code') or '').strip().upper()
    note = data.get('note', '')

    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    try:
        file_record = update_session_file_note(_db_path(), owner_code, file_id, note)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    if not file_record:
        return jsonify({'ok': False, 'error': 'File not found or access denied.'}), 404

    return jsonify({'ok': True, 'file': file_record_to_json(file_record)})


@session_bp.route('/api/session/<owner_code>/name', methods=['PATCH'])
def api_rename_session(owner_code):
    """Rename a session (owner only)."""
    owner_code = owner_code.upper()
    data = request.get_json(silent=True) or {}
    session_name = data.get('session_name', '')

    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    session = rename_session(_db_path(), owner_code, session_name)
    if not session:
        return jsonify({'ok': False, 'error': 'Session not found.'}), 404

    return jsonify({
        'ok': True,
        'session_name': session['session_name'] or '',
    })


@session_bp.route('/api/session/<owner_code>/reorder', methods=['PATCH'])
def api_reorder(owner_code):
    """Reorder session files (owner only). file_ids: top-to-bottom display order."""
    owner_code = owner_code.upper()
    data = request.get_json(silent=True) or {}
    file_ids = data.get('file_ids', [])

    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    if not isinstance(file_ids, list):
        return jsonify({'ok': False, 'error': 'Invalid file order.'}), 400

    if reorder_session_files(_db_path(), owner_code, file_ids):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Could not reorder files.'}), 400


@session_bp.route('/api/session/<owner_code>/close', methods=['POST'])
def api_close_session(owner_code):
    """Close and delete a session (owner only)."""
    owner_code = owner_code.upper()
    if not is_valid_session_code(owner_code):
        return jsonify({'ok': False, 'error': 'Invalid owner code.'}), 403

    if close_session(_db_path(), _storage_path(), owner_code):
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Session not found.'}), 404


@session_bp.route('/session/download/<viewer_code>/<int:file_id>')
def download_viewer_file(viewer_code, file_id):
    """Download a file from a session (viewer access)."""
    viewer_code = viewer_code.upper()
    session = get_session_by_viewer_code(_db_path(), viewer_code)
    if not session:
        abort(404)

    file_record = get_session_file(_db_path(), file_id)
    if not file_record or file_record['session_id'] != session['id']:
        abort(404)

    if not file_record['file_path'] or not os.path.exists(file_record['file_path']):
        abort(404)

    return send_file(
        file_record['file_path'],
        as_attachment=True,
        download_name=file_record['original_filename'],
    )


@session_bp.route('/session/owner-download/<owner_code>/<int:file_id>')
def download_owner_file(owner_code, file_id):
    """Download a file from a session (owner access)."""
    owner_code = owner_code.upper()
    session = get_session_by_owner_code(_db_path(), owner_code)
    if not session:
        abort(404)

    file_record = get_session_file(_db_path(), file_id)
    if not file_record or file_record['session_id'] != session['id']:
        abort(404)

    if not file_record['file_path'] or not os.path.exists(file_record['file_path']):
        abort(404)

    return send_file(
        file_record['file_path'],
        as_attachment=True,
        download_name=file_record['original_filename'],
    )
