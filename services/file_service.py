"""Shared file upload and storage helpers."""

import os

from werkzeug.utils import secure_filename


def save_uploaded_file(file_storage, target_dir):
    """
    Save a single uploaded file to target_dir with a unique sanitized name.
    Returns dict with filename, original_filename, file_path, file_size or None if invalid.
    """
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    os.makedirs(target_dir, exist_ok=True)

    base_name, ext = os.path.splitext(filename)
    counter = 1
    original_filename = filename
    while os.path.exists(os.path.join(target_dir, filename)):
        filename = f'{base_name}_{counter}{ext}'
        counter += 1

    file_path = os.path.join(target_dir, filename)
    file_storage.save(file_path)
    file_size = os.path.getsize(file_path)

    return {
        'filename': filename,
        'original_filename': original_filename,
        'file_path': file_path,
        'file_size': file_size,
    }


def format_file_size(file_size):
    """Format byte size for display."""
    if file_size < 1024:
        return f'{file_size} B'
    if file_size < 1024 * 1024:
        return f'{file_size / 1024:.1f} KB'
    return f'{file_size / 1024 / 1024:.1f} MB'
