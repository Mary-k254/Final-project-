import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import init_db, get_db_connection
from ai_utils import init_ai_models, detect_mood_from_text, generate_chat_response
from utils import generate_food_mood_insights, MOOD_EMOJIS

app = Flask(__name__)
# Set secret key from environment variable or generate a random one
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Initialize database and AI models
init_db()
sentiment_model, emotion_tokenizer, emotion_model = init_ai_models()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Validate inputs
        if not username or not email or not password:
            return render_template('signup.html', error="All fields are required")
        
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters")
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        # Insert user into database
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
            return render_template('signup.html', error="Username or email already exists")
    
    return render_template('signup.html')

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
            return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

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
    
    # Get recent food logs
    recent_foods = conn.execute(
        'SELECT * FROM food_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    # Get recent mood logs
    recent_moods = conn.execute(
        'SELECT * FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    # Get insights
    insights = generate_food_mood_insights(user_id)
    
    conn.close()
    
    return render_template(
        'dashboard.html',
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
            return render_template('log_food.html', username=session['username'], error="Food name is required")
        
        # Convert calories to int if provided
        if calories:
            try:
                calories = int(calories)
            except ValueError:
                return render_template('log_food.html', username=session['username'], error="Calories must be a number")
        else:
            calories = None
        
        # Insert food log
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO food_logs (user_id, food_name, calories) VALUES (?, ?, ?)',
            (session['user_id'], food_name, calories)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('log_food.html', username=session['username'])

@app.route('/log_mood', methods=['GET', 'POST'])
def log_mood():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        mood = request.form['mood']
        intensity = request.form['intensity']
        
        if not mood or not intensity:
            return render_template('log_mood.html', username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="All fields are required")
        
        try:
            intensity = int(intensity)
            if intensity < 1 or intensity > 5:
                return render_template('log_mood.html', username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be between 1 and 5")
        except ValueError:
            return render_template('log_mood.html', username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS, error="Intensity must be a number")
        
        # Insert mood log
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO mood_logs (user_id, mood, intensity) VALUES (?, ?, ?)',
            (session['user_id'], mood, intensity)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('log_mood.html', username=session['username'], moods=MOOD_EMOJIS.keys(), mood_emojis=MOOD_EMOJIS)

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
    
    # Reverse to show in chronological order
    chat_history = list(reversed(chat_history))
    
    return render_template(
        'chat.html',
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
    
    # Detect mood from message
    detected_mood = detect_mood_from_text(user_message, sentiment_model, emotion_tokenizer, emotion_model)
    
    # Generate response
    response = generate_chat_response(user_message, detected_mood)
    
    # Save to database
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

@app.route('/insights')
def insights():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    insights = generate_food_mood_insights(user_id)
    
    return render_template(
        'insights.html',
        username=session['username'],
        insights=insights
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
