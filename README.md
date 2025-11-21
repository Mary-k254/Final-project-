# Mood Bite

A web application that helps you track your food intake and mood to discover connections between what you eat and how you feel.

## Features

- User authentication (signup/login)
- Food logging with calorie tracking
- Mood logging with intensity levels
- AI-powered chat for mood detection
- Personalized insights based on food-mood correlations

## Deployment on Render

### Prerequisites

1. A Render account
2. A PostgreSQL database (Render provides free PostgreSQL databases)

### Steps

1. **Create a PostgreSQL Database on Render**
   - Go to your Render dashboard
   - Click "New" → "PostgreSQL"
   - Give it a name (e.g., "mood-bite-db")
   - Copy the "Internal Database URL" after creation

2. **Deploy the Web Service**
   - Connect your GitHub repository to Render
   - Create a new "Web Service"
   - Select your repository
   - Configure the service:
     - **Build Command**: `pip install -r requirements.txt && python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"`
     - **Start Command**: `gunicorn app:app`
     - **Environment Variables**:
       - `DATABASE_URL`: Paste your PostgreSQL Internal Database URL
       - `SECRET_KEY`: Generate a random string (e.g., using `python -c "import os; print(os.urandom(24).hex())"`)
       - `PYTHON_VERSION`: `3.11.0`

3. **Deploy**
   - Click "Create Web Service"
   - Wait for the deployment to complete

## Local Development

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"
   ```

4. Create a `.env` file based on `.env.example`:
   ```
   DATABASE_URL=postgresql://localhost/mood_bite
   SECRET_KEY=your-secret-key-here
   PORT=5000
   ```

5. Set up local PostgreSQL database:
   ```bash
   createdb mood_bite
   ```

6. Run the application:
   ```bash
   python app.py
   ```

7. Visit `http://localhost:5000`

## Technologies Used

- Flask (Web Framework)
- PostgreSQL (Database)
- TextBlob (Sentiment Analysis)
- Bootstrap 5 (UI)
- Gunicorn (Production Server)

## License

MIT
