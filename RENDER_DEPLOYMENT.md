# Render.com Deployment Guide

## 🚀 Quick Deploy to Render

### Method 1: Using render.yaml (Recommended)

1. **Push your code to GitHub** (if not already done)
2. **Connect to Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file

### Method 2: Manual Setup

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository**
3. **Configure the service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Python Version**: 3.10 or higher

4. **Set Environment Variables**:
   ```
   SECRET_KEY=your-secret-key-here
   MAX_CONTENT_LENGTH_MB=200
   DROP_EXPIRY_HOURS=24
   RENDER=true
   ```

## 🔧 Troubleshooting Database Issues

### Problem: Database not persisting
**Solution**: The app now uses Render's persistent storage directory (`/opt/render/project/src`)

### Problem: Can't create drops
**Solution**: Check the health endpoint at `https://your-app.onrender.com/health`

### Debugging Steps:

1. **Check the health endpoint**:
   ```
   https://your-app-name.onrender.com/health
   ```
   This will show you:
   - Database path and existence
   - Storage directory status
   - Current drop count
   - Environment variables

2. **Check Render logs**:
   - Go to your service dashboard
   - Click on "Logs" tab
   - Look for database initialization messages

3. **Verify environment variables**:
   - Ensure `RENDER=true` is set
   - Check that `SECRET_KEY` is properly configured

## 📁 File Structure for Render

```
your-repo/
├── app.py                 # Main application
├── requirements.txt       # Dependencies (includes gunicorn)
├── Procfile              # Alternative deployment config
├── render.yaml           # Render-specific configuration
├── templates/            # HTML templates
└── README.md
```

## 🔍 Health Check Endpoint

The app includes a health check endpoint at `/health` that provides:

```json
{
  "status": "healthy",
  "database_path": "/opt/render/project/src/drops.db",
  "storage_path": "/opt/render/project/src/storage",
  "database_exists": true,
  "storage_exists": true,
  "drop_count": 0,
  "render_env": "true"
}
```

## 🛠️ Common Issues & Solutions

### Issue 1: "Database not found"
**Cause**: Database file not being created in persistent storage
**Solution**: 
- Ensure `RENDER=true` environment variable is set
- Check that the app is using the correct database path
- Verify the health endpoint shows correct paths

### Issue 2: "Permission denied"
**Cause**: Insufficient permissions for file operations
**Solution**: 
- Render handles permissions automatically
- Ensure you're using the correct storage paths

### Issue 3: "Drops not persisting"
**Cause**: Using ephemeral storage instead of persistent
**Solution**: 
- The app now automatically detects Render environment
- Uses `/opt/render/project/src` for persistent storage

## 📊 Monitoring

### Logs to Watch:
- Database initialization messages
- File upload success/failure
- Storage directory creation
- Health check responses

### Key Metrics:
- Database file size
- Number of active drops
- Storage directory usage
- Response times

## 🔄 Updates and Maintenance

### Updating the App:
1. Push changes to GitHub
2. Render automatically redeploys
3. Database and files persist across deployments

### Database Maintenance:
- Expired drops are automatically cleaned up
- No manual maintenance required
- Monitor storage usage in Render dashboard

## 🚨 Important Notes

1. **Free Tier Limitations**:
   - 750 hours/month
   - Sleeps after 15 minutes of inactivity
   - 512MB RAM limit

2. **File Storage**:
   - Files are stored in persistent directory
   - Automatic cleanup after expiration
   - Monitor storage usage

3. **Database**:
   - SQLite database persists across deployments
   - Automatic initialization on first run
   - No external database required

## 🆘 Getting Help

If you're still having issues:

1. **Check the health endpoint**: `https://your-app.onrender.com/health`
2. **Review Render logs** for error messages
3. **Verify environment variables** are set correctly
4. **Test locally** with `RENDER=true` environment variable

The app should now work correctly on Render with persistent database and file storage!
