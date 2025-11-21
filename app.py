import os
import datetime
import json
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from jinja2 import Template
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
from collections import defaultdict
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import nltk

load_dotenv()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/brown')
except LookupError:
    nltk.download('brown')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Mood to emoji mapping
MOOD_EMOJIS = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
    "anxious": "😰",
    "excited": "🤩",
    "tired": "😴",
    "calm": "😌",
    "confused": "😕",
    "neutral": "😐"
}

# HTML Templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <a href="/login" class="btn btn-outline-primary me-2">Login</a>
                <a href="/signup" class="btn btn-primary">Sign Up</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <div class="text-center">
            <h1 class="display-4 fw-bold mb-4">Track Your Food, Understand Your Mood</h1>
            <p class="lead mb-5">Mood Bite helps you discover the connection between what you eat and how you feel.</p>
            <a href="/signup" class="btn btn-primary btn-lg">Get Started</a>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

SIGNUP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sign Up - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
        </div>
    </nav>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <h2 class="mb-4">Sign Up</h2>
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Sign Up</button>
                    <a href="/login" class="btn btn-link">Already have an account?</a>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
        </div>
    </nav>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <h2 class="mb-4">Login</h2>
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                    <a href="/signup" class="btn btn-link">Create an account</a>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <span class="me-3">Welcome, {{ username }}!</span>
                <a href="/logout" class="btn btn-outline-danger">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <div class="row">
            <div class="col-md-4">
                <a href="/log_food" class="btn btn-primary w-100 mb-2">Log Food</a>
                <a href="/log_mood" class="btn btn-success w-100 mb-2">Log Mood</a>
                <a href="/chat" class="btn btn-info w-100 mb-2">AI Chat</a>
                <a href="/insights" class="btn btn-warning w-100">View Insights</a>
            </div>
            <div class="col-md-8">
                <h3>Recent Food Logs</h3>
                <ul class="list-group mb-4">
                    {% for food in recent_foods %}
                    <li class="list-group-item">{{ food['food_name'] }} - {{ food['calories'] or 'N/A' }} cal - {{ food['timestamp'] }}</li>
                    {% endfor %}
                    {% if not recent_foods %}
                    <li class="list-group-item">No food logs yet</li>
                    {% endif %}
                </ul>
                <h3>Recent Mood Logs</h3>
                <ul class="list-group mb-4">
                    {% for mood in recent_moods %}
                    <li class="list-group-item">{{ mood_emojis[mood['mood']] }} {{ mood['mood'] }} ({{ mood['intensity'] }}/5) - {{ mood['timestamp'] }}</li>
                    {% endfor %}
                    {% if not recent_moods %}
                    <li class="list-group-item">No mood logs yet</li>
                    {% endif %}
                </ul>
                <h3>Insights</h3>
                <ul class="list-group">
                    {% for insight in insights %}
                    <li class="list-group-item">{{ insight }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOG_FOOD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Log Food - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                <a href="/logout" class="btn btn-outline-danger">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <h2 class="mb-4">Log Food</h2>
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Food Name</label>
                        <input type="text" class="form-control" name="food_name" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Calories (optional)</label>
                        <input type="number" class="form-control" name="calories">
                    </div>
                    <button type="submit" class="btn btn-primary">Log Food</button>
                    <a href="/dashboard" class="btn btn-secondary">Cancel</a>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOG_MOOD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Log Mood - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                <a href="/logout" class="btn btn-outline-danger">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <h2 class="mb-4">Log Mood</h2>
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Mood</label>
                        <select class="form-select" name="mood" required>
                            {% for mood in moods %}
                            <option value="{{ mood }}">{{ mood_emojis[mood] }} {{ mood }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Intensity (1-5)</label>
                        <input type="number" class="form-control" name="intensity" min="1" max="5" required>
                    </div>
                    <button type="submit" class="btn btn-success">Log Mood</button>
                    <a href="/dashboard" class="btn btn-secondary">Cancel</a>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

CHAT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Chat - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                <a href="/logout" class="btn btn-outline-danger">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <h2 class="mb-4">AI Chat</h2>
        <div id="chat-history" class="mb-4" style="height: 400px; overflow-y: scroll; border: 1px solid #ddd; padding: 15px;">
            {% for chat in chat_history %}
            <div class="mb-3">
                <strong>You:</strong> {{ chat['message'] }}<br>
                <strong>AI {{ mood_emojis[chat['detected_mood']] }}:</strong> {{ chat['response'] }}
            </div>
            {% endfor %}
        </div>
        <div class="input-group">
            <input type="text" id="message-input" class="form-control" placeholder="Type your message...">
            <button onclick="sendMessage()" class="btn btn-primary">Send</button>
        </div>
    </div>
    <script>
    function sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value;
        if (!message) return;

        fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: message})
        })
        .then(res => res.json())
        .then(data => {
            const chatHistory = document.getElementById('chat-history');
            chatHistory.innerHTML += `<div class="mb-3"><strong>You:</strong> ${message}<br><strong>AI ${data.mood_emoji}:</strong> ${data.response}</div>`;
            chatHistory.scrollTop = chatHistory.scrollHeight;
            input.value = '';
        });
    }
    document.getElementById('message-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
    </script>
</body>
</html>
"""

INSIGHTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Insights - Mood Bite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Mood Bite</a>
            <div class="ms-auto">
                <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                <a href="/logout" class="btn btn-outline-danger">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container my-5">
        <h2 class="mb-4">Your Insights</h2>
        <ul class="list-group">
            {% for insight in insights %}
            <li class="list-group-item">{{ insight }}</li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
"""

# Database functions
def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://localhost/mood_bite')

def init_db():
    database_url = get_database_url()
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS food_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        food_name TEXT NOT NULL,
        calories INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mood_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        mood TEXT NOT NULL,
        intensity INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        detected_mood TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    database_url = get_database_url()
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    return conn

# AI functions using TextBlob
def detect_mood_from_text(text):
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        # Check for specific keywords
        text_lower = text.lower()
        if any(word in text_lower for word in ['angry', 'furious', 'mad', 'annoyed']):
            return "angry"
        elif any(word in text_lower for word in ['anxious', 'worried', 'nervous', 'scared', 'afraid']):
            return "anxious"
        elif any(word in text_lower for word in ['tired', 'exhausted', 'sleepy', 'fatigue']):
            return "tired"
        elif any(word in text_lower for word in ['excited', 'thrilled', 'enthusiastic']):
            return "excited"
        elif any(word in text_lower for word in ['calm', 'peaceful', 'relaxed']):
            return "calm"

        # Use polarity for general sentiment
        if polarity > 0.5:
            return "happy"
        elif polarity < -0.3:
            return "sad"
        elif polarity > 0.2:
            return "calm"
        else:
            return "neutral"
    except Exception as e:
        logger.error(f"Error detecting mood: {str(e)}")
        return "neutral"

def generate_chat_response(user_message, detected_mood):
    if detected_mood == "happy":
        return "I'm glad you're feeling happy! What did you eat today that might be contributing to your good mood?"
    elif detected_mood == "sad":
        return "I'm sorry to hear you're feeling down. Sometimes what we eat can affect our mood. Have you noticed any patterns with your food choices?"
    elif detected_mood == "angry":
        return "It sounds like you're feeling frustrated. Would you like to talk about what's bothering you? Also, have you logged your meals today?"
    elif detected_mood == "anxious":
        return "Feeling anxious can be tough. Have you tried logging your meals? Sometimes certain foods can help reduce anxiety."
    elif detected_mood == "excited":
        return "Your excitement is contagious! What's making you feel this way? Have you logged any special meals recently?"
    elif detected_mood == "tired":
        return "Feeling tired might be related to your diet. Have you been eating enough nutritious foods? Let's check your food logs."
    elif detected_mood == "calm":
        return "It's great that you're feeling calm. What foods do you think contribute to this peaceful state?"
    else:
        return "Thanks for sharing. How has your diet been lately? Remember, what we eat can affect how we feel."

# Utility functions
def generate_food_mood_insights(user_id):
    conn = get_db_connection()
    
    food_logs = conn.execute(
        'SELECT * FROM food_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20',
        (user_id,)
    ).fetchall()
    
    mood_logs = conn.execute(
        'SELECT * FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20',
        (user_id,)
    ).fetchall()
    
    food_mood_map = defaultdict(list)
    
    for food in food_logs:
        food_time = datetime.datetime.strptime(food['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        for mood in mood_logs:
            mood_time = datetime.datetime.strptime(mood['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_diff = (mood_time - food_time).total_seconds() / 3600
            
            if 0 <= time_diff <= 2:
                food_mood_map[food['food_name']].append((mood['mood'], mood['intensity']))
    
    insights = []
    
    if food_mood_map:
        for food, moods in food_mood_map.items():
            mood_counts = defaultdict(int)
            total_intensity = 0
            
            for mood, intensity in moods:
                mood_counts[mood] += 1
                total_intensity += intensity
            
            most_common_mood = max(mood_counts, key=mood_counts.get)
            avg_intensity = total_intensity / len(moods)
            
            if most_common_mood in ["happy", "excited", "calm"] and avg_intensity > 3:
                insights.append(f"Eating {food} seems to boost your mood!")
            elif most_common_mood in ["sad", "angry", "anxious"] and avg_intensity > 3:
                insights.append(f"You might want to avoid {food} as it seems to negatively affect your mood.")
    
    if not insights:
        insights.append("Log more food and mood entries to get personalized insights!")
    
    conn.close()
    return insights

# AI models are now lightweight (TextBlob)
ai_models_loaded = True

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    logger.error("App will continue but may not function properly without database.")

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(INDEX_TEMPLATE)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            return Template(SIGNUP_TEMPLATE).render(error="All fields are required")

        if len(password) < 6:
            return Template(SIGNUP_TEMPLATE).render(error="Password must be at least 6 characters")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.close()
            return Template(SIGNUP_TEMPLATE).render(error="Username or email already exists")

    return Template(SIGNUP_TEMPLATE).render(error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return Template(LOGIN_TEMPLATE).render(error="Invalid username or password")

    return Template(LOGIN_TEMPLATE).render(error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    recent_foods = conn.execute(
        'SELECT * FROM food_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    recent_moods = conn.execute(
        'SELECT * FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    insights = generate_food_mood_insights(user_id)
    
    conn.close()
    
    return Template(DASHBOARD_TEMPLATE).render(
        username=session['username'],
        recent_foods=recent_foods,
        recent_moods=recent_moods,
        insights=insights,
        mood_emojis=MOOD_EMOJIS
    )

@app.route('/log_food', methods=['GET', 'POST'])
def log_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        food_name = request.form['food_name']
        calories = request.form.get('calories')
        
        if not food_name:
            return Template(LOG_FOOD_TEMPLATE).render(username=session['username'], error="Food name is required")

        if calories:
            try:
                calories = int(calories)
            except ValueError:
                return Template(LOG_FOOD_TEMPLATE).render(username=session['username'], error="Calories must be a number")
        else:
            calories = None

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO food_logs (user_id, food_name, calories) VALUES (?, ?, ?)',
            (session['user_id'], food_name, calories)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return Template(LOG_FOOD_TEMPLATE).render(username=session['username'], error=None)

@app.route('/log_mood', methods=['GET', 'POST'])
def log_mood():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        intensity = request.form['intensity']
        
        if not mood or not intensity:
            return Template(LOG_MOOD_TEMPLATE).render(username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="All fields are required")

        try:
            intensity = int(intensity)
            if intensity < 1 or intensity > 5:
                return Template(LOG_MOOD_TEMPLATE).render(username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be between 1 and 5")
        except ValueError:
            return Template(LOG_MOOD_TEMPLATE).render(username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be a number")

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO mood_logs (user_id, mood, intensity) VALUES (?, ?, ?)',
            (session['user_id'], mood, intensity)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return Template(LOG_MOOD_TEMPLATE).render(username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error=None)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    chat_history = conn.execute(
        'SELECT * FROM chat_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    chat_history = list(reversed(chat_history))
    
    return Template(CHAT_TEMPLATE).render(
        username=session['username'],
        chat_history=chat_history,
        mood_emojis=MOOD_EMOJIS
    )

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        detected_mood = detect_mood_from_text(user_message)
        response = generate_chat_response(user_message, detected_mood)
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO chat_logs (user_id, message, response, detected_mood) VALUES (?, ?, ?, ?)',
            (session['user_id'], user_message, response, detected_mood)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "response": response,
            "detected_mood": detected_mood,
            "mood_emoji": MOOD_EMOJIS.get(detected_mood, "😐")
        })
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({
            "response": "I'm sorry, there was an error processing your message. Please try again.",
            "detected_mood": "neutral",
            "mood_emoji": MOOD_EMOJIS.get("neutral", "😐")
        })

@app.route('/insights')
def insights():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    insights = generate_food_mood_insights(user_id)
    
    return Template(INSIGHTS_TEMPLATE).render(
        username=session['username'],
        insights=insights
    )

@app.route('/health')
def health_check():
    status = {
        "status": "ok",
        "database": "connected",
        "ai_models": "loaded" if ai_models_loaded else "not_loaded"
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    return jsonify(status)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
