import os
import sqlite3
import datetime
import json
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
from collections import defaultdict
import logging

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

# HTML Templates (simplified for brevity - you can use the full templates from the previous code)
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

# Add other templates similarly (LOGIN_TEMPLATE, SIGNUP_TEMPLATE, etc.) - use the full versions from previous code

# Database functions
def init_db():
    conn = sqlite3.connect('mood_bite.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        food_name TEXT NOT NULL,
        calories INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mood TEXT NOT NULL,
        intensity INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn = sqlite3.connect('mood_bite.db')
    conn.row_factory = sqlite3.Row
    return conn

# AI functions
def init_ai_models():
    try:
        logger.info("Loading sentiment analysis model...")
        sentiment_model = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            tokenizer="distilbert-base-uncased-finetuned-sst-2-english"
        )
        logger.info("Sentiment analysis model loaded successfully.")
        
        logger.info("Loading emotion detection model...")
        emotion_tokenizer = AutoTokenizer.from_pretrained("bhadresh-savani/bert-base-uncased-emotion")
        emotion_model = AutoModelForSequenceClassification.from_pretrained("bhadresh-savani/bert-base-uncased-emotion")
        logger.info("Emotion detection model loaded successfully.")
        
        return sentiment_model, emotion_tokenizer, emotion_model
    except Exception as e:
        logger.error(f"Error loading AI models: {str(e)}")
        raise

def detect_mood_from_text(text, sentiment_model, emotion_tokenizer, emotion_model):
    try:
        sentiment_result = sentiment_model(text)[0]
        sentiment = sentiment_result['label']
        score = sentiment_result['score']
        
        inputs = emotion_tokenizer(text, return_tensors="pt")
        outputs = emotion_model(**inputs)
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        emotions = emotion_model.config.id2label
        emotion = emotions[torch.argmax(predictions).item()]
        
        if emotion == "joy" or (sentiment == "POSITIVE" and score > 0.8):
            return "happy"
        elif emotion == "sadness" or (sentiment == "NEGATIVE" and score > 0.8):
            return "sad"
        elif emotion == "anger":
            return "angry"
        elif emotion == "fear":
            return "anxious"
        elif emotion == "love":
            return "excited"
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

# Initialize database and AI models
init_db()

# Initialize AI models with error handling
try:
    logger.info("Initializing AI models...")
    sentiment_model, emotion_tokenizer, emotion_model = init_ai_models()
    ai_models_loaded = True
    logger.info("AI models initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize AI models: {str(e)}")
    ai_models_loaded = False
    sentiment_model = None
    emotion_tokenizer = None
    emotion_model = None

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
            return render_template_string(SIGNUP_TEMPLATE, error="All fields are required")
        
        if len(password) < 6:
            return render_template_string(SIGNUP_TEMPLATE, error="Password must be at least 6 characters")
        
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
        except sqlite3.IntegrityError:
            conn.close()
            return render_template_string(SIGNUP_TEMPLATE, error="Username or email already exists")
    
    return render_template_string(SIGNUP_TEMPLATE)

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
            return render_template_string(LOGIN_TEMPLATE, error="Invalid username or password")
    
    return render_template_string(LOGIN_TEMPLATE)

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
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
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
            return render_template_string(LOG_FOOD_TEMPLATE, username=session['username'], error="Food name is required")
        
        if calories:
            try:
                calories = int(calories)
            except ValueError:
                return render_template_string(LOG_FOOD_TEMPLATE, username=session['username'], error="Calories must be a number")
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
    
    return render_template_string(LOG_FOOD_TEMPLATE, username=session['username'])

@app.route('/log_mood', methods=['GET', 'POST'])
def log_mood():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        intensity = request.form['intensity']
        
        if not mood or not intensity:
            return render_template_string(LOG_MOOD_TEMPLATE, username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="All fields are required")
        
        try:
            intensity = int(intensity)
            if intensity < 1 or intensity > 5:
                return render_template_string(LOG_MOOD_TEMPLATE, username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be between 1 and 5")
        except ValueError:
            return render_template_string(LOG_MOOD_TEMPLATE, username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be a number")
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO mood_logs (user_id, mood, intensity) VALUES (?, ?, ?)',
            (session['user_id'], mood, intensity)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template_string(LOG_MOOD_TEMPLATE, username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS)

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
    
    return render_template_string(
        CHAT_TEMPLATE,
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
    
    if not ai_models_loaded:
        return jsonify({
            "response": "I'm sorry, the AI models are currently unavailable. Please try again later.",
            "detected_mood": "neutral",
            "mood_emoji": MOOD_EMOJIS.get("neutral", "😐")
        })
    
    try:
        detected_mood = detect_mood_from_text(user_message, sentiment_model, emotion_tokenizer, emotion_model)
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
    
    return render_template_string(
        INSIGHTS_TEMPLATE,
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
        conn.execute('SELECT 1')
        conn.close()
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    return jsonify(status)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
