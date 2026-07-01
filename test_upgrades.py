#!/usr/bin/env python3
"""Integration tests for Drop App upgrades."""

import os
import re
import tempfile
from io import BytesIO

# Isolate test database and storage
os.environ['DATABASE_PATH'] = tempfile.mktemp(suffix='.db')
os.environ['STORAGE_PATH'] = tempfile.mkdtemp()

from app import app, init_db  # noqa: E402


def run_tests():
    init_db()
    client = app.test_client()

    r = client.get('/')
    assert r.status_code == 200
    assert b'Create Drop' in r.data
    assert b'Session Drop' in r.data
    print('home OK')

    r = client.post('/send', data={'text_content': 'hello'})
    assert r.status_code == 200
    assert b'Drop Created Successfully' in r.data
    assert b'Scan to open drop' in r.data
    print('send OK')

    match = re.search(rb'class="code">(\d{4})</div>', r.data)
    assert match, 'drop code not found'
    code = match.group(1).decode()

    r = client.get(f'/qr/drop/{code}.png')
    assert r.status_code == 200
    assert r.data[:8] == b'\x89PNG\r\n\x1a\n'
    print('qr OK')

    r = client.get(f'/d/{code}')
    assert r.status_code == 200
    print('view drop OK')

    r = client.post('/session/create', data={'session_name': 'Test Session'})
    assert r.status_code == 200
    assert b'Session Drop Created' in r.data

    owner_match = re.search(
        rb'class="code"[^>]*>([23456789ABCDEFGHJKMNPQRSTUVWXYZ]{16})</div>',
        r.data,
    )
    viewer_match = re.search(
        rb'class="code"[^>]*>([23456789ABCDEFGHJKMNPQRSTUVWXYZ]{16})</div>',
        r.data[owner_match.end():] if owner_match else r.data,
    )
    assert owner_match and viewer_match
    owner_code = owner_match.group(1).decode()
    viewer_code = viewer_match.group(1).decode()
    print('session created OK')

    r = client.get(f'/session/manage/{owner_code}')
    assert r.status_code == 200
    assert b'Owner Dashboard' in r.data
    print('manage OK')

    data = {
        'file': (BytesIO(b'test content'), 'test.txt'),
        'note': 'My note',
    }
    r = client.post(
        f'/api/session/upload/{owner_code}',
        data=data,
        content_type='multipart/form-data',
    )
    assert r.status_code == 200
    payload = r.get_json()
    assert payload['ok']
    assert payload['file']['original_filename'] == 'test.txt'
    file_id = payload['file']['id']
    print('upload OK')

    r = client.get(f'/session/view/{viewer_code}')
    assert r.status_code == 200
    assert b'test.txt' in r.data
    assert b'My note' in r.data
    print('viewer OK')

    r = client.get(f'/session/download/{viewer_code}/{file_id}')
    assert r.status_code == 200
    print('download OK')

    r = client.delete(
        f'/api/session/file/{file_id}',
        json={'owner_code': owner_code},
    )
    assert r.status_code == 200
    assert r.get_json()['ok']
    print('delete OK')

    r = client.post(f'/api/session/{owner_code}/close')
    assert r.status_code == 200
    print('close OK')

    print('ALL TESTS PASSED')
    return True


if __name__ == '__main__':
    run_tests()
