# Send ↔ Receive Drop Service

A production-ready Python Flask web application for sharing files and text via unique 4-digit codes.

## Features

- **Simple Interface**: Two-column layout for sending and receiving
- **Multiple File Support**: Upload any file type with size limits
- **Text Sharing**: Paste and share raw text content
- **Unique Codes**: 4-digit codes (0000-9999) with collision handling
- **Auto-Expiration**: Files automatically deleted after configurable hours
- **ZIP Downloads**: Download all files as a single ZIP archive
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Security**: Input validation, filename sanitization, and safe file handling

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access the Application**
   Open your browser to `http://localhost:5000`

### Environment Variables

Configure the application using environment variables:

```bash
# Required for production
export SECRET_KEY="your-secret-key-here"

# Optional configuration
export MAX_CONTENT_LENGTH_MB=200
export DROP_EXPIRY_HOURS=24
export DATABASE_PATH="drops.db"
export STORAGE_PATH="storage"
```

## Deployment

### Heroku

1. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

2. **Set Environment Variables**
   ```bash
   heroku config:set SECRET_KEY="your-secret-key-here"
   heroku config:set MAX_CONTENT_LENGTH_MB=200
   heroku config:set DROP_EXPIRY_HOURS=24
   ```

3. **Deploy**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

### Other Platforms

The application includes a `Procfile` for Gunicorn deployment and can be deployed to any platform that supports Python/Flask:

- **Railway**: Connect your GitHub repository
- **Render**: Use the Procfile for automatic deployment
- **DigitalOcean App Platform**: Deploy with the Procfile
- **AWS Elastic Beanstalk**: Use the Procfile for worker configuration

## API Endpoints

- `GET /` - Home page with send/receive interface
- `POST /send` - Create a new drop with files and/or text
- `POST /receive` - Submit code to access a drop
- `GET /d/<code>` - View drop content and files
- `GET /download/<code>/<filename>` - Download a specific file
- `GET /download_all/<code>.zip` - Download all files as ZIP

## Configuration

### File Limits
- Default: 200MB per request
- Configurable via `MAX_CONTENT_LENGTH_MB`

### Expiration
- Default: 24 hours
- Configurable via `DROP_EXPIRY_HOURS`

### Storage
- Files stored in `storage/<code>/` directories
- SQLite database for metadata
- Automatic cleanup of expired drops

## Security Considerations

⚠️ **Important Security Notes:**

1. **Not for Sensitive Data**: 4-digit codes provide limited security
2. **File Validation**: Basic filename sanitization only
3. **No Authentication**: Anyone with the code can access the drop
4. **Temporary Storage**: Files are automatically deleted after expiration

## Development

### Project Structure

```
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Deployment configuration
├── templates/         # HTML templates
│   ├── base.html
│   ├── home.html
│   ├── send_success.html
│   ├── drop.html
│   ├── drop_not_found.html
│   └── 404.html
├── storage/           # File storage (created automatically)
└── drops.db          # SQLite database (created automatically)
```

### Database Schema

**drops table:**
- `id` - Primary key
- `code` - Unique 4-digit code
- `text_content` - Shared text content
- `created_at` - Creation timestamp
- `expires_at` - Expiration timestamp
- `file_count` - Number of files

**files table:**
- `id` - Primary key
- `drop_code` - Foreign key to drops.code
- `filename` - Sanitized filename
- `original_filename` - Original filename
- `file_size` - File size in bytes
- `created_at` - Creation timestamp

## License

This project is open source and available under the MIT License.
