from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

def init_ai_models():
    # Load sentiment analysis model
    sentiment_model = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        tokenizer="distilbert-base-uncased-finetuned-sst-2-english"
    )
    
    # Load emotion detection model
    emotion_tokenizer = AutoTokenizer.from_pretrained("bhadresh-savani/bert-base-uncased-emotion")
    emotion_model = AutoModelForSequenceClassification.from_pretrained("bhadresh-savani/bert-base-uncased-emotion")
    
    return sentiment_model, emotion_tokenizer, emotion_model

def detect_mood_from_text(text, sentiment_model, emotion_tokenizer, emotion_model):
    # Use sentiment analysis to get a basic mood
    sentiment_result = sentiment_model(text)[0]
    sentiment = sentiment_result['label']
    score = sentiment_result['score']
    
    # Use emotion detection for more specific emotions
    inputs = emotion_tokenizer(text, return_tensors="pt")
    outputs = emotion_model(**inputs)
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
    emotions = emotion_model.config.id2label
    emotion = emotions[torch.argmax(predictions).item()]
    
    # Map to our mood categories
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

def generate_chat_response(user_message, detected_mood):
    # Simple rule-based responses based on detected mood
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
