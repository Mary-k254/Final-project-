# Quick Start - Deploy to Render in 5 Minutes

## What's Fixed
Your code now works on Render. Main fixes:
- Removed 500MB AI models (replaced with lightweight TextBlob)
- Changed SQLite to PostgreSQL
- Added all missing HTML templates
- Fixed all import and dependency issues

## Deploy Now

### 1. Create Database (2 minutes)
1. Go to https://dashboard.render.com
2. Click **New** → **PostgreSQL**
3. Name it: `mood-bite-db`
4. Click **Create Database**
5. Copy the **Internal Database URL**

### 2. Deploy App (3 minutes)
1. Click **New** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Build Command**:
     ```
     pip install -r requirements.txt && python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"
     ```
   - **Start Command**:
     ```
     gunicorn app:app
     ```

4. Add Environment Variables:
   - `DATABASE_URL` = (paste your database URL)
   - `SECRET_KEY` = (run this command to generate):
     ```
     python -c "import os; print(os.urandom(24).hex())"
     ```

5. Click **Create Web Service**

### 3. Wait & Test
- Wait 5-10 minutes for build
- Click your app URL
- Sign up and test!

## Need Help?
See DEPLOYMENT.md for detailed troubleshooting.
