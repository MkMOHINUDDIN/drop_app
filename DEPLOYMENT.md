# Deployment Guide - Send ↔ Receive Drop Service

## Quick Start (Local Development)

1. **Clone or download the project files**
2. **Run the setup script:**
   ```bash
   python deploy.py
   ```
3. **Start the application:**
   ```bash
   python app.py
   ```
4. **Open your browser to:** `http://localhost:5000`

## Production Deployment

### Heroku Deployment

1. **Install Heroku CLI** and login:
   ```bash
   heroku login
   ```

2. **Create a new Heroku app:**
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   heroku config:set MAX_CONTENT_LENGTH_MB=200
   heroku config:set DROP_EXPIRY_HOURS=24
   ```

4. **Deploy:**
   ```bash
   git init
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

5. **Open your app:**
   ```bash
   heroku open
   ```

### Railway Deployment

1. **Connect your GitHub repository** to Railway
2. **Set environment variables** in Railway dashboard:
   - `SECRET_KEY`: Generate with `python -c 'import secrets; print(secrets.token_hex(32))'`
   - `MAX_CONTENT_LENGTH_MB`: 200
   - `DROP_EXPIRY_HOURS`: 24
3. **Deploy automatically** - Railway will detect the Procfile

### Render Deployment

1. **Create a new Web Service** on Render
2. **Connect your repository**
3. **Configure:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. **Set environment variables** in Render dashboard
5. **Deploy**

### DigitalOcean App Platform

1. **Create a new app** on DigitalOcean
2. **Connect your repository**
3. **Configure:**
   - Source Directory: `/`
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `gunicorn app:app`
4. **Set environment variables**
5. **Deploy**

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key (REQUIRED for production) |
| `MAX_CONTENT_LENGTH_MB` | `200` | Maximum file size per request in MB |
| `DROP_EXPIRY_HOURS` | `24` | Hours until drops expire |
| `DATABASE_PATH` | `drops.db` | SQLite database file path |
| `STORAGE_PATH` | `storage` | Directory for file storage |

## Security Checklist

- [ ] Set a strong `SECRET_KEY` in production
- [ ] Configure appropriate file size limits
- [ ] Set up HTTPS (handled by most PaaS providers)
- [ ] Monitor disk usage (files are auto-deleted)
- [ ] Consider rate limiting for production use
- [ ] Review and adjust expiration times as needed

## Monitoring

### Health Check Endpoint
The application doesn't include a health check endpoint, but you can monitor:
- Database file size (`drops.db`)
- Storage directory size (`storage/`)
- Application logs

### Logs
Monitor application logs for:
- File upload errors
- Database connection issues
- Expired drop cleanup

## Scaling Considerations

- **Database**: SQLite is suitable for small to medium traffic
- **File Storage**: Local storage works for single-instance deployments
- **Memory**: Each request loads files into memory for ZIP creation
- **Cleanup**: Expired drops are cleaned up on each request

For high-traffic deployments, consider:
- PostgreSQL for the database
- Cloud storage (S3, etc.) for files
- Background job processing for cleanup
- Load balancing with sticky sessions

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'flask'"**
   - Run: `pip install -r requirements.txt`

2. **"Permission denied" errors**
   - Ensure write permissions for `storage/` directory
   - Check database file permissions

3. **"Request entity too large" errors**
   - Increase `MAX_CONTENT_LENGTH_MB` or reduce file sizes

4. **Database locked errors**
   - Ensure only one instance is running
   - Check for proper database connection handling

### Debug Mode
For development, the app runs in debug mode by default. For production:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Support

For issues or questions:
1. Check the application logs
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Test locally before deploying
