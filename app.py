#!/usr/bin/env python3
"""
Send ↔ Receive Drop Service
A production-ready Flask web application for sharing files and text via unique codes.
"""

import os
import sqlite3
import secrets
import zipfile
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from flask import Flask, request, render_template, redirect, url_for, send_file, flash, abort
import json

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH_MB = int(os.environ.get('MAX_CONTENT_LENGTH_MB', 200))
    DROP_EXPIRY_HOURS = int(os.environ.get('DROP_EXPIRY_HOURS', 24))
    
    # Use Render's persistent storage directory if available, otherwise use local
    if os.environ.get('RENDER'):
        # Render.com deployment
        DATABASE_PATH = os.path.join('/opt/render/project/src', 'drops.db')
        STORAGE_PATH = os.path.join('/opt/render/project/src', 'storage')
    else:
        # Local development
        DATABASE_PATH = os.environ.get('DATABASE_PATH', 'drops.db')
        STORAGE_PATH = os.environ.get('STORAGE_PATH', 'storage')
    
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024  # Convert to bytes

app = Flask(__name__)
app.config.from_object(Config)

# Ensure storage directory exists
os.makedirs(app.config['STORAGE_PATH'], exist_ok=True)

def init_db():
    """Initialize the SQLite database with required tables."""
    # Ensure the directory exists
    db_dir = os.path.dirname(app.config['DATABASE_PATH'])
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            text_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            file_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drop_code TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (drop_code) REFERENCES drops (code) ON DELETE CASCADE
        )
    ''')
    
    # Create index for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_drops_code ON drops (code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_drops_expires ON drops (expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_drop_code ON files (drop_code)')
    
    conn.commit()
    conn.close()
    
    # Log database initialization
    app.logger.info(f"Database initialized at: {app.config['DATABASE_PATH']}")
    app.logger.info(f"Database file exists: {os.path.exists(app.config['DATABASE_PATH'])}")

def generate_unique_code():
    """Generate a unique 4-digit code with collision handling."""
    max_attempts = 100
    for _ in range(max_attempts):
        code = f"{secrets.randbelow(10000):04d}"
        
        # Check if code already exists and is not expired
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM drops WHERE code = ? AND expires_at > ?',
            (code, datetime.now())
        )
        if not cursor.fetchone():
            conn.close()
            return code
        conn.close()
    
    raise Exception("Unable to generate unique code after maximum attempts")

def cleanup_expired_drops():
    """Remove expired drops and their associated files."""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    # Get expired drop codes
    cursor.execute('SELECT code FROM drops WHERE expires_at <= ?', (datetime.now().isoformat(),))
    expired_codes = [row[0] for row in cursor.fetchall()]
    
    # Remove files from disk and database
    for code in expired_codes:
        drop_path = os.path.join(app.config['STORAGE_PATH'], code)
        if os.path.exists(drop_path):
            shutil.rmtree(drop_path)
        
        cursor.execute('DELETE FROM files WHERE drop_code = ?', (code,))
    
    # Remove expired drops
    cursor.execute('DELETE FROM drops WHERE expires_at <= ?', (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()

def get_drop_info(code):
    """Get drop information if valid and not expired."""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT text_content, created_at, expires_at, file_count
        FROM drops WHERE code = ? AND expires_at > ?
    ''', (code, datetime.now().isoformat()))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    # Parse datetime strings back to datetime objects
    created_at = datetime.fromisoformat(result[1]) if result[1] else None
    expires_at = datetime.fromisoformat(result[2]) if result[2] else None
    
    return {
        'text_content': result[0],
        'created_at': created_at,
        'expires_at': expires_at,
        'file_count': result[3]
    }

def get_drop_files(code):
    """Get list of files for a drop."""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT filename, original_filename, file_size, created_at
        FROM files WHERE drop_code = ? ORDER BY created_at
    ''', (code,))
    
    files = []
    for row in cursor.fetchall():
        files.append({
            'filename': row[0],
            'original_filename': row[1],
            'file_size': row[2],
            'created_at': row[3]
        })
    
    conn.close()
    return files

@app.route('/')
def home():
    """Home page with Send and Receive sections."""
    return render_template('home.html')

@app.route('/health')
def health():
    """Health check endpoint for debugging."""
    try:
        # Check database
        db_exists = os.path.exists(app.config['DATABASE_PATH'])
        storage_exists = os.path.exists(app.config['STORAGE_PATH'])
        
        # Test database connection
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM drops')
        drop_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            'status': 'healthy',
            'database_path': app.config['DATABASE_PATH'],
            'storage_path': app.config['STORAGE_PATH'],
            'database_exists': db_exists,
            'storage_exists': storage_exists,
            'drop_count': drop_count,
            'render_env': os.environ.get('RENDER', 'false')
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'database_path': app.config['DATABASE_PATH'],
            'storage_path': app.config['STORAGE_PATH'],
            'render_env': os.environ.get('RENDER', 'false')
        }, 500

@app.route('/send', methods=['POST'])
def send():
    """Handle file uploads and text submission."""
    try:
        # Log the request
        app.logger.info(f"Send request received. Database path: {app.config['DATABASE_PATH']}")
        app.logger.info(f"Storage path: {app.config['STORAGE_PATH']}")
        app.logger.info(f"Database exists: {os.path.exists(app.config['DATABASE_PATH'])}")
        # Get text content
        text_content = request.form.get('text_content', '').strip()
        
        # Get uploaded files
        files = request.files.getlist('files')
        
        # Validate that at least one of text or files is provided
        if not text_content and not any(f.filename for f in files):
            flash('Please provide either text content or upload at least one file.', 'error')
            return redirect(url_for('home'))
        
        # Generate unique code
        code = generate_unique_code()
        
        # Create drop directory
        drop_path = os.path.join(app.config['STORAGE_PATH'], code)
        os.makedirs(drop_path, exist_ok=True)
        
        # Calculate expiration time
        expires_at = datetime.now() + timedelta(hours=app.config['DROP_EXPIRY_HOURS'])
        
        # Save to database
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO drops (code, text_content, expires_at, file_count)
            VALUES (?, ?, ?, ?)
        ''', (code, text_content, expires_at.isoformat(), len([f for f in files if f.filename])))
        
        # Save files
        file_count = 0
        for file in files:
            if file and file.filename:
                # Sanitize filename
                filename = secure_filename(file.filename)
                if not filename:
                    continue
                
                # Ensure unique filename in case of duplicates
                base_name, ext = os.path.splitext(filename)
                counter = 1
                original_filename = filename
                while os.path.exists(os.path.join(drop_path, filename)):
                    filename = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                # Save file
                file_path = os.path.join(drop_path, filename)
                file.save(file_path)
                
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Save file info to database
                cursor.execute('''
                    INSERT INTO files (drop_code, filename, original_filename, file_size)
                    VALUES (?, ?, ?, ?)
                ''', (code, filename, original_filename, file_size))
                
                file_count += 1
        
        conn.commit()
        conn.close()
        
        # Clean up expired drops
        cleanup_expired_drops()
        
        return render_template('send_success.html', code=code, expires_at=expires_at)
        
    except Exception as e:
        app.logger.error(f"Error in send endpoint: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return redirect(url_for('home'))

@app.route('/receive', methods=['POST'])
def receive():
    """Handle code submission and redirect to drop page."""
    code = request.form.get('code', '').strip()
    
    if not code or len(code) != 4 or not code.isdigit():
        flash('Please enter a valid 4-digit code.', 'error')
        return redirect(url_for('home'))
    
    return redirect(url_for('view_drop', code=code))

@app.route('/d/<code>')
def view_drop(code):
    """Display the drop page with content and files."""
    # Validate code format
    if len(code) != 4 or not code.isdigit():
        abort(404)
    
    # Get drop info
    drop_info = get_drop_info(code)
    if not drop_info:
        return render_template('drop_not_found.html', code=code)
    
    # Get files
    files = get_drop_files(code)
    
    return render_template('drop.html', 
                         code=code, 
                         drop_info=drop_info, 
                         files=files)

@app.route('/download/<code>/<filename>')
def download_file(code, filename):
    """Download a specific file from a drop."""
    # Validate code format
    if len(code) != 4 or not code.isdigit():
        abort(404)
    
    # Check if drop exists and is not expired
    drop_info = get_drop_info(code)
    if not drop_info:
        abort(404)
    
    # Check if file exists in database
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    cursor.execute('''
        SELECT original_filename FROM files 
        WHERE drop_code = ? AND filename = ?
    ''', (code, filename))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        abort(404)
    
    # Get file path
    file_path = os.path.join(app.config['STORAGE_PATH'], code, filename)
    if not os.path.exists(file_path):
        abort(404)
    
    return send_file(file_path, as_attachment=True, download_name=result[0])

@app.route('/download_all/<code>.zip')
def download_all(code):
    """Download all files from a drop as a ZIP archive."""
    # Validate code format
    if len(code) != 4 or not code.isdigit():
        abort(404)
    
    # Check if drop exists and is not expired
    drop_info = get_drop_info(code)
    if not drop_info:
        abort(404)
    
    # Get files
    files = get_drop_files(code)
    if not files:
        abort(404)
    
    # Create temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in files:
                file_path = os.path.join(app.config['STORAGE_PATH'], code, file_info['filename'])
                if os.path.exists(file_path):
                    zipf.write(file_path, file_info['original_filename'])
        
        return send_file(temp_zip.name, 
                        as_attachment=True, 
                        download_name=f'drop_{code}.zip',
                        mimetype='application/zip')
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_zip.name)
        except:
            pass

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    """Handle file size limit exceeded."""
    flash(f'File size exceeds the limit of {app.config["MAX_CONTENT_LENGTH_MB"]} MB.', 'error')
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Clean up expired drops on startup
    cleanup_expired_drops()
    
    # Log startup information
    app.logger.info(f"Starting app with database: {app.config['DATABASE_PATH']}")
    app.logger.info(f"Storage directory: {app.config['STORAGE_PATH']}")
    app.logger.info(f"Render environment: {os.environ.get('RENDER', 'false')}")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
