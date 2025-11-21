# Deployment Guide for Render

## What Was Fixed

The original code had several critical issues preventing deployment on Render:

1. **Missing HTML Templates** - Template variables were referenced but not defined
2. **Heavy AI Models** - Transformers and PyTorch models (500MB+) caused deployment timeouts and memory issues
3. **SQLite Database** - SQLite doesn't work on Render's ephemeral filesystem
4. **Dependency Issues** - Outdated and incompatible package versions

## Changes Made

### 1. Replaced Heavy AI Models
- **Before**: transformers + torch (500MB+)
- **After**: TextBlob (lightweight, <5MB)
- Simplified sentiment analysis using polarity scores and keyword detection

### 2. Database Migration
- **Before**: SQLite3 (local file-based)
- **After**: PostgreSQL (cloud-compatible)
- Updated all database queries to use psycopg2
- Added proper connection handling with environment variables

### 3. Added All HTML Templates
- LOGIN_TEMPLATE
- SIGNUP_TEMPLATE
- DASHBOARD_TEMPLATE
- LOG_FOOD_TEMPLATE
- LOG_MOOD_TEMPLATE
- CHAT_TEMPLATE
- INSIGHTS_TEMPLATE

### 4. Updated Dependencies
```
Flask==3.0.0
Werkzeug==3.0.1
gunicorn==21.2.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
textblob==0.17.1
nltk==3.8.1
```

### 5. Added Configuration Files
- `Procfile` - Tells Render how to start the app
- `runtime.txt` - Specifies Python version
- `.env.example` - Template for environment variables
- `README.md` - Documentation

## Deployment Steps on Render

### Step 1: Create PostgreSQL Database

1. Log into your Render dashboard
2. Click **"New"** → **"PostgreSQL"**
3. Configure:
   - Name: `mood-bite-db`
   - Region: Choose closest to you
   - Plan: Free
4. Click **"Create Database"**
5. Wait for creation and copy the **Internal Database URL**

### Step 2: Deploy Web Service

1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `mood-bite`
   - **Region**: Same as database
   - **Branch**: `main` (or your branch)
   - **Runtime**: Python 3
   - **Build Command**:
     ```
     pip install -r requirements.txt && python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"
     ```
   - **Start Command**:
     ```
     gunicorn app:app
     ```

### Step 3: Set Environment Variables

Add these environment variables in Render:

1. `DATABASE_URL`: Paste your PostgreSQL Internal Database URL
2. `SECRET_KEY`: Generate with:
   ```bash
   python -c "import os; print(os.urandom(24).hex())"
   ```
3. `PYTHON_VERSION`: `3.11.0`

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Install dependencies
   - Download NLTK data
   - Initialize database tables
   - Start the application

3. Monitor the logs for any errors
4. Once deployed, click the URL to access your app

## Troubleshooting

### Database Connection Errors
- Ensure `DATABASE_URL` is set correctly
- Use the **Internal Database URL**, not External
- Check that database and web service are in the same region

### Build Timeouts
- The build should complete in 5-10 minutes
- If it times out, check the build logs
- Ensure all dependencies are in requirements.txt

### Application Crashes
- Check logs: Dashboard → Your Service → Logs
- Common issues:
  - Missing environment variables
  - Database connection failures
  - NLTK data not downloaded

### NLTK Download Errors
If NLTK data fails to download during build, manually trigger it:
```bash
python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"
```

## Testing Your Deployment

1. Visit your app URL
2. Click **"Sign Up"** and create an account
3. Log in with your credentials
4. Try logging food and mood entries
5. Test the AI chat feature
6. Check the insights page

## Health Check

Your app includes a health check endpoint:
```
GET /health
```

Response:
```json
{
  "status": "ok",
  "database": "connected",
  "ai_models": "loaded"
}
```

## Post-Deployment

### Monitoring
- Set up Render's auto-deploy from GitHub
- Monitor logs regularly
- Check health endpoint periodically

### Scaling
- Free tier: 750 hours/month
- Upgrade to paid plan for:
  - No sleeping (free tier sleeps after 15 min)
  - More memory
  - Better performance

### Backups
- Render automatically backs up PostgreSQL databases
- Set up automated backups in database settings

## Local Development After Changes

To test locally with the new PostgreSQL setup:

1. Install PostgreSQL locally
2. Create database: `createdb mood_bite`
3. Update `.env`:
   ```
   DATABASE_URL=postgresql://localhost/mood_bite
   SECRET_KEY=your-secret-key
   PORT=5000
   ```
4. Run: `python app.py`

## Support

If you encounter issues:
1. Check Render logs
2. Verify environment variables
3. Test database connection
4. Review this deployment guide
