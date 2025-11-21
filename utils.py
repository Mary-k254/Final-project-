from collections import defaultdict
from datetime import datetime
from models import get_db_connection

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

def generate_food_mood_insights(user_id):
    conn = get_db_connection()
    
    # Get food logs
    food_logs = conn.execute(
        'SELECT * FROM food_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20',
        (user_id,)
    ).fetchall()
    
    # Get mood logs
    mood_logs = conn.execute(
        'SELECT * FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20',
        (user_id,)
    ).fetchall()
    
    # Simple correlation analysis
    food_mood_map = defaultdict(list)
    
    for food in food_logs:
        food_time = datetime.strptime(food['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # Find moods within 2 hours after eating
        for mood in mood_logs:
            mood_time = datetime.strptime(mood['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_diff = (mood_time - food_time).total_seconds() / 3600  # hours
            
            if 0 <= time_diff <= 2:
                food_mood_map[food['food_name']].append((mood['mood'], mood['intensity']))
    
    # Generate insights
    insights = []
    
    if food_mood_map:
        for food, moods in food_mood_map.items():
            mood_counts = defaultdict(int)
            total_intensity = 0
            
            for mood, intensity in moods:
                mood_counts[mood] += 1
                total_intensity += intensity
            
            # Find the most common mood
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
