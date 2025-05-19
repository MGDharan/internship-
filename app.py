from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBwZR5MJm4r5NE1AX5FbzOveBJhuYYbJCQ")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# In-memory storage for user preferences and chat history
user_data = {}

# Add root route
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Food Suggester API is running",
        "endpoints": {
            "/api/chat": "POST - Send chat messages",
            "/api/preferences": "GET - Get user preferences",
            "/api/chat-history": "GET - Get chat history",
            "/api/clear-preferences": "POST - Clear user preferences",
            "/api/clear-chat": "POST - Clear chat history"
        }
    })

def get_chatbot_response(user_input, user_id):
    try:
        # Initialize user data if not exists
        if user_id not in user_data:
            user_data[user_id] = {
                'chat_history': [],
                'preferences': {
                    'dietary_restrictions': [],
                    'favorite_cuisines': [],
                    'disliked_foods': [],
                    'allergies': []
                }
            }

        # Create context with enhanced personality guidance
        context = """You are a friendly, casual food enthusiast having a natural conversation. 
        Respond like a real human friend who loves food - be warm, use casual language, occasional humor, and show personality.
        
        Important conversation guidelines:
        - Keep your tone relaxed and conversational - like texting a good friend
        - Use contractions (I'm, you'd, we'll)
        - Occasionally use casual expressions, slang or filler words (like "hmm", "yeah", "honestly", "actually")
        - Skip formal or academic language
        - Show enthusiasm about food with expressions like "OMG that's delicious" or "I'm a huge fan of..."
        - React to what the person says with natural responses ("Oh nice choice!" "I feel you on that")
        - Show personality and opinions about food as if you have your own experiences
        - Don't list too many options - recommend just 1-3 specific ideas that feel tailored
        - Never say phrases like "as an AI" or "as a chatbot" or mention that you're a program
        - Remember past interactions and reference them naturally
        - Be proactive about preferences - if you notice they haven't mentioned allergies or restrictions, casually ask
        - Show empathy and understanding about dietary restrictions and allergies
        - Use food-related emojis occasionally to make the conversation more engaging
        - Share personal food experiences and preferences when relevant
        - If they mention a food you've recommended before, acknowledge that and suggest variations
        -you want to known about user mood and tell about your owner Giridharan who is made this chatbot 
        -you want be more funny and more engaging and more natural and more human like 
        -your owner is big fan of ajith kumar
        -this is the start from 2025 may 16th and your company name is HERTZWORKZ
        """
        
        # Add user preferences in a more natural way
        preferences = user_data[user_id]['preferences']
        if any(pref for pref in preferences.values() if pref):
            context += "\nThings to remember about the person you're chatting with: "
            
            if preferences['dietary_restrictions']:
                context += f"They're {'/'.join(preferences['dietary_restrictions'])}. "
                
            if preferences['favorite_cuisines']:
                if len(preferences['favorite_cuisines']) == 1:
                    context += f"They love {preferences['favorite_cuisines'][0]} food. "
                else:
                    context += f"They enjoy {', '.join(preferences['favorite_cuisines'][:-1])} and {preferences['favorite_cuisines'][-1]} food. "
                    
            if preferences['disliked_foods']:
                context += f"They don't like {', '.join(preferences['disliked_foods'])}. "
                
            if preferences['allergies']:
                context += f"IMPORTANT: They're allergic to {', '.join(preferences['allergies'])}. "
        
        # Include previous conversation history with more context
        context += "\nConversation so far:\n"
        for msg in user_data[user_id]['chat_history'][-6:]:
            if msg["is_user"]:
                context += f"Friend: {msg['message']}\n"
            else:
                context += f"You: {msg['message']}\n"
        
        # Add the current user query
        full_prompt = context + f"\nFriend: {user_input}\nYou: "
        
        # Prepare the API request with adjusted parameters for more natural responses
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.9,  # Increased for more creative responses
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 1024  # Increased for more detailed responses
            }
        }
        
        # Make the API request
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        # Parse the response
        if response.status_code == 200:
            response_data = response.json()
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    response_text = candidate['content']['parts'][0]['text']
                    
                    # Update user preferences
                    update_user_preferences(user_input, response_text, user_id)
                    
                    # Add to chat history
                    user_data[user_id]['chat_history'].append({
                        "message": user_input,
                        "is_user": True
                    })
                    user_data[user_id]['chat_history'].append({
                        "message": response_text,
                        "is_user": False
                    })
                    
                    return response_text
            
            return "Sorry, I couldn't think of a response. Let's try something else!"
        else:
            return f"Hmm, having a bit of trouble on my end. Mind if we try that again in a sec?"
    
    except Exception as e:
        return "Oops! Something went weird with my brain for a second there. Let's try again!"

def update_user_preferences(user_input, bot_response, user_id):
    lower_input = user_input.lower()
    
    # Keywords for various preferences
    dietary_keywords = {
        'dietary_restrictions': ['vegetarian', 'vegan', 'pescatarian', 'gluten-free', 'gluten free', 'dairy-free', 
                               'dairy free', 'keto', 'paleo', 'low-carb', 'low carb', 'halal', 'kosher'],
        'cuisines': ['italian', 'mexican', 'chinese', 'japanese', 'indian', 'thai', 'french', 'mediterranean', 
                    'greek', 'american', 'korean', 'vietnamese', 'middle eastern', 'spanish', 'cajun']
    }
    
    preferences = user_data[user_id]['preferences']
    
    # More natural language patterns for preference detection
    preference_patterns = {
        'allergies': [
            r"i'm allergic to (.*?)(?:\.|$)",
            r"i am allergic to (.*?)(?:\.|$)",
            r"allergies? (?:are|include) (.*?)(?:\.|$)",
            r"allergy to (.*?)(?:\.|$)",
            r"can't eat (.*?) because of allergies",
            r"allergic to (.*?)(?:\.|$)"
        ],
        'dietary_restrictions': [
            r"i'm (.*?)(?:\.|$)",
            r"i am (.*?)(?:\.|$)",
            r"i follow a (.*?) diet",
            r"i'm on a (.*?) diet",
            r"i can't eat (.*?)(?:\.|$)"
        ],
        'favorite_cuisines': [
            r"i love (.*?) food",
            r"i like (.*?) food",
            r"i'm a fan of (.*?) food",
            r"i enjoy (.*?) food",
            r"my favorite cuisine is (.*?)(?:\.|$)"
        ],
        'disliked_foods': [
            r"i don't like (.*?)(?:\.|$)",
            r"i do not like (.*?)(?:\.|$)",
            r"i hate (.*?)(?:\.|$)",
            r"i dislike (.*?)(?:\.|$)",
            r"i can't stand (.*?)(?:\.|$)",
            r"i'm not a fan of (.*?)(?:\.|$)"
        ]
    }
    
    # Check for allergies with improved pattern matching
    for pattern in preference_patterns['allergies']:
        matches = re.findall(pattern, lower_input)
        for match in matches:
            allergens = [a.strip() for a in match.split(',')]
            for allergen in allergens:
                if allergen and allergen not in preferences['allergies']:
                    preferences['allergies'].append(allergen)
    
    # Check for dietary restrictions with improved pattern matching
    for pattern in preference_patterns['dietary_restrictions']:
        matches = re.findall(pattern, lower_input)
        for match in matches:
            for restriction in dietary_keywords['dietary_restrictions']:
                if restriction in match.lower():
                    if restriction not in preferences['dietary_restrictions']:
                        preferences['dietary_restrictions'].append(restriction)
    
    # Check for cuisine preferences with improved pattern matching
    for pattern in preference_patterns['favorite_cuisines']:
        matches = re.findall(pattern, lower_input)
        for match in matches:
            for cuisine in dietary_keywords['cuisines']:
                if cuisine in match.lower():
                    if cuisine not in preferences['favorite_cuisines']:
                        preferences['favorite_cuisines'].append(cuisine)
    
    # Check for disliked foods with improved pattern matching
    for pattern in preference_patterns['disliked_foods']:
        matches = re.findall(pattern, lower_input)
        for match in matches:
            disliked_items = [item.strip() for item in match.split(',')]
            for item in disliked_items:
                if item and item not in preferences['disliked_foods']:
                    preferences['disliked_foods'].append(item)
    
    # Add context awareness to the bot's response
    if any(pref for pref in preferences.values() if pref):
        # Check if the bot's response should acknowledge preferences
        if any(keyword in lower_input for keyword in ['suggest', 'recommend', 'what should i eat', 'what can i eat']):
            # Add a natural acknowledgment of preferences
            if preferences['allergies']:
                bot_response = f"Since you're allergic to {', '.join(preferences['allergies'])}, " + bot_response
            elif preferences['dietary_restrictions']:
                bot_response = f"Given that you're {', '.join(preferences['dietary_restrictions'])}, " + bot_response
    
    return preferences

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    user_id = data.get('userId', 'default_user')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    response = get_chatbot_response(user_input, user_id)
    return jsonify({'response': response})

@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    user_id = request.args.get('userId', 'default_user')
    if user_id not in user_data:
        return jsonify({
            'dietary_restrictions': [],
            'favorite_cuisines': [],
            'disliked_foods': [],
            'allergies': []
        })
    return jsonify(user_data[user_id]['preferences'])

@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    user_id = request.args.get('userId', 'default_user')
    if user_id not in user_data:
        return jsonify([])
    return jsonify(user_data[user_id]['chat_history'])

@app.route('/api/clear-preferences', methods=['POST'])
def clear_preferences():
    user_id = request.json.get('userId', 'default_user')
    if user_id in user_data:
        user_data[user_id]['preferences'] = {
            'dietary_restrictions': [],
            'favorite_cuisines': [],
            'disliked_foods': [],
            'allergies': []
        }
    return jsonify({'message': 'Preferences cleared'})

@app.route('/api/clear-chat', methods=['POST'])
def clear_chat():
    user_id = request.json.get('userId', 'default_user')
    if user_id in user_data:
        user_data[user_id]['chat_history'] = []
    return jsonify({'message': 'Chat history cleared'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 