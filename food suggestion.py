import csv
import os
import random
import requests
import datetime
import time
import schedule
import threading
from plyer import notification
from twilio.rest import Client

# === API Keys and Configuration ===
WEATHER_API_KEY = "dffaccbef5bb4312a1950640252404"
PUSHBULLET_TOKEN = "o.qXOywmPdeEReyFn8t4evGvOey1TvlnyS"
TWILIO_ACCOUNT_SID = "ENTER YOUR TWILIO ACCOUNT"
TWILIO_AUTH_TOKEN = "ENTER YOUR TOKEN"
TWILIO_FROM = "ENTER YOUR TWILIO FROM"
DATA_FILE = "user_suggestions.csv"

# Time of day definitions (24-hour format)
TIME_PERIODS = {
    "morning": (5, 11),    # 5:00 AM to 11:59 AM
    "afternoon": (12, 16), # 12:00 PM to 4:59 PM
    "evening": (17, 23)    # 5:00 PM to 11:59 PM
}

# === Food Database ===
FOOD_DATABASE = {
    "hot": {
        "morning": [
            ("Chilled Fruit Bowl - Start your day cool", 30, "quick bite"),
            ("Yogurt Parfait - Light and refreshing", 35, "quick bite"),
            ("Cold Brew Coffee - Smooth and energizing", 25, "drink"),
            ("Overnight Oats - Cool and nutritious", 40, "full meal"),
            ("Fruit Smoothie - Icy and rejuvenating", 30, "drink")
        ],
        "afternoon": [
            ("Cucumber Sandwich - Light and fresh", 35, "quick bite"),
            ("Watermelon Salad - Summer on a plate", 45, "starter"),
            ("Chilled Gazpacho - Spanish cool classic", 50, "starter"),
            ("Greek Salad - Mediterranean freshness", 55, "full meal"),
            ("Iced Green Tea - Antioxidant cooler", 20, "drink")
        ],
        "evening": [
            ("Refreshing Chilled Mango Delight - A tropical escape!", 40, "dessert"),
            ("Creamy Ice Cream Sundae - Your sweet cool-down", 60, "dessert"),
            ("Frozen Yogurt - Guilt-free chill scoop", 55, "dessert"),
            ("Watermelon Sorbet - Nature's cool refreshment", 45, "dessert"),
            ("Mint Lemonade - Zesty citrus cooler", 30, "drink")
        ]
    },
    "cold": {
        "morning": [
            ("Hot Oatmeal - Warming start to day", 40, "full meal"),
            ("Masala Chai - Spiced warmth in a cup", 30, "drink"),
            ("Poha - Light Indian breakfast", 45, "full meal"),
            ("Scrambled Eggs - Protein-rich start", 40, "full meal"),
            ("Cinnamon Toast - Sweet morning comfort", 35, "quick bite")
        ],
        "afternoon": [
            ("Tomato Soup - Simple warming classic", 45, "starter"),
            ("Grilled Cheese Sandwich - Melty comfort", 40, "quick bite"),
            ("Hot Noodle Bowl - Asian comfort food", 60, "full meal"),
            ("Baked Potatoes - Hearty and filling", 50, "side"),
            ("Hot Chocolate - Rich and warming", 30, "drink")
        ],
        "evening": [
            ("Spicy Chicken Biryani - Hot and flavorful!", 120, "full meal"),
            ("Masala Dosa with Chutney - Crisp and spicy", 40, "quick bite"),
            ("Hot Chocolate - Perfect for the cold weather", 60, "drink"),
            ("Ginger Soup - Warming and aromatic", 55, "starter"),
            ("Buttery Garlic Bread - Toasty comfort food", 35, "quick bite")
        ]
    },
    "moderate": {
        "morning": [
            ("Avocado Toast - Trendy breakfast choice", 40, "quick bite"),
            ("Fruit and Granola - Balanced breakfast", 35, "quick bite"),
            ("Vegetable Omelette - Protein-packed start", 45, "full meal"),
            ("Banana Pancakes - Sweet morning treat", 50, "full meal"),
            ("Green Smoothie - Nutritious energy booster", 30, "drink")
        ],
        "afternoon": [
            ("Caesar Salad - Classic lunch option", 50, "full meal"),
            ("Vegetable Wrap - Portable and healthy", 45, "full meal"),
            ("Mushroom Pasta - Savory and satisfying", 60, "full meal"),
            ("Lentil Soup - Protein-rich comfort", 50, "starter"),
            ("Iced Tea - Refreshing afternoon sip", 25, "drink")
        ],
        "evening": [
            ("Aromatic Veg Pulao - Fragrant and wholesome", 70, "full meal"),
            ("Chapati with Veg Kurma - Comfort food", 60, "full meal"),
            ("Veg Soup - Healthy and hearty", 50, "starter"),
            ("Garden Salad - Fresh and nutritious", 45, "starter"),
            ("Pasta Primavera - Italian classic", 80, "full meal")
        ]
    }
}


# === Helper Functions ===
def get_current_temperature(location):
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}"
        response = requests.get(url)
        data = response.json()
        temperature = data["current"]["temp_c"]
        condition = data["current"]["condition"]["text"]
        print(f"\n📊 Current Weather in {location}: {condition} at {temperature}°C")
        return temperature, condition
    except Exception as e:
        print(f"⚠️ Weather API error: {e}")
        return 25, "Unknown"  # Default fallback

def get_temperature_category(temp):
    if temp >= 35:
        return "hot"
    elif temp <= 20:
        return "cold"
    else:
        return "moderate"

def get_time_period(hour):
    """Determine whether it's morning, afternoon, or evening based on hour (0-23)"""
    for period, (start, end) in TIME_PERIODS.items():
        if start <= hour <= end:
            return period
    return "morning"  # Default fallback

def read_csv():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline='', encoding='utf-8') as file:
        return list(csv.reader(file))[1:]  # Skip header

def save_to_csv(data_row):
    file_exists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "Name", "Phone", "Location", "Weather", "Temperature",
                "Category", "Suggested Food", "Timestamp", "TimePeriod"  # Added TimePeriod
            ])
        writer.writerow(data_row)

def get_recent_suggestions(name, phone, days=1, time_period=None):
    """Get suggestions made to this user in the last specified days, optionally filtered by time period"""
    dataset = read_csv()
    now = datetime.datetime.now()
    
    recent_suggestions = []
    
    for row in dataset:
        if row[0] == name and row[1] == phone:
            try:
                # Parse the timestamp
                suggestion_time = datetime.datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
                
                # Get the time period for this suggestion
                row_time_period = row[8] if len(row) > 8 else get_time_period(suggestion_time.hour)
                
                # Check if it's within the specified days and matches time period (if specified)
                days_diff = (now - suggestion_time).days
                if days_diff <= days and (time_period is None or row_time_period == time_period):
                    recent_suggestions.append(row[6])  # Add food suggestion
            except Exception:
                pass  # Skip invalid timestamps
                
    return recent_suggestions

def get_unique_suggestion(category, time_period, previous_foods, food_type=None):
    # Get time-specific food options
    time_specific_options = FOOD_DATABASE[category][time_period]
    
    # Filter by not previously suggested and matching type if specified
    filtered = [
        food for food in time_specific_options
        if food[0] not in previous_foods and (food_type is None or food[2] == food_type)
    ]
    
    # If we still have options, return a new one
    if filtered:
        return random.choice(filtered)
    
    # If no unique suggestions left, fallback to any from same time period and type
    fallback_same_type = [
        food for food in time_specific_options
        if food_type is None or food[2] == food_type
    ]
    
    # Final fallback to any food from this time period
    return random.choice(fallback_same_type) if fallback_same_type else random.choice(time_specific_options)

def show_popup_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Notification error: {e}")

def send_sms_notification(to_phone, message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=to_phone
        )
        print(f"📲 SMS sent to {to_phone}")
    except Exception as e:
        print(f"⚠️ Failed to send SMS: {e}")

def format_time_for_message(time_string):
    dt = datetime.datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%I:%M %p on %b %d, %Y")

# === Automated Suggestion Function ===
def send_auto_suggestion(name, phone, location, scheduled_time, food_type=None):
    try:
        print(f"\n🔄 Sending automated suggestion to {name} at {phone} (scheduled for {scheduled_time})")
        
        # Get current time information
        now = datetime.datetime.now()
        current_hour = now.hour
        time_period = get_time_period(current_hour)
        
        temperature, weather = get_current_temperature(location)
        category = get_temperature_category(temperature)
        
        # Get recent suggestions for this specific time period to avoid repeating
        recent_suggestions = get_recent_suggestions(name, phone, days=1, time_period=time_period)
        print(f"🚫 Avoiding recent suggestions for {time_period}: {recent_suggestions}")
        
        # Get unique suggestion for this time period
        suggestion = get_unique_suggestion(category, time_period, recent_suggestions, food_type)
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_time = format_time_for_message(current_time)
        
        # Save data with timestamp and time period
        save_to_csv([name, phone, location, weather, temperature, category, suggestion[0], current_time, time_period])
        
        # Create message with time period-specific greeting
        greeting = "Good morning" if time_period == "morning" else "Good afternoon" if time_period == "afternoon" else "Good evening"
        sms_message = f"🍽️ {greeting}, {name}! Here's your {time_period} food suggestion for {temperature}°C in {location}: {suggestion[0]} (sent at {formatted_time})"
        send_sms_notification(phone, sms_message)
        
        print(f"✅ Automated {time_period} suggestion sent to {name}: {suggestion[0]}")
        return True
    except Exception as e:
        print(f"⚠️ Auto-suggestion error for {name}: {e}")
        return False

# === Schedule Next Day Suggestions ===
def schedule_next_day_suggestion(name, phone, location, time_str, food_type=None):
    try:
        # Parse the original timestamp to extract hour and minute
        dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        scheduled_time = dt.strftime("%H:%M")
        time_period = get_time_period(dt.hour)
        
        # Schedule task for same time tomorrow
        job_id = f"{name}_{phone}_{scheduled_time}"
        
        # Create a unique job for this user at this time
        schedule.every().day.at(scheduled_time).do(
            send_auto_suggestion, name, phone, location, scheduled_time, food_type
        ).tag(job_id)
        
        print(f"🔔 Scheduled {time_period} suggestion for {name} tomorrow at {scheduled_time}")
        return True
    except Exception as e:
        print(f"⚠️ Scheduling error: {e}")
        return False

# === Run the scheduler in background ===
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# === Main Interactive Function ===
def interactive_food_suggester():
    try:
        name = input("Enter your name: ").strip()
        number = input("Enter your phone number (with country code, e.g. +91): ").strip()
        location = input("Enter your location (city name): ").strip()

        # Get current time information
        now = datetime.datetime.now()
        current_hour = now.hour
        time_period = get_time_period(current_hour)
        
        temperature, weather = get_current_temperature(location)
        category = get_temperature_category(temperature)
        
        # Get recent suggestions for this specific time period
        recent_suggestions = get_recent_suggestions(name, number, days=1, time_period=time_period)
        
        dataset = read_csv()
        user_exists = any(row[0] == name and row[1] == number for row in dataset)
        
        # If new user, ask preference
        food_type = None
        if not user_exists:
            print("do you want auto or manual")
            print("\n🌟 Welcome! What type of food do you prefer?")
            print("Options: full meal / quick bite / dessert / starter / drink")
            food_type = input("Enter your preference: ").strip().lower()

        # Get a suggestion avoiding recent ones for this time period
        suggestion = get_unique_suggestion(category, time_period, recent_suggestions, food_type)
        
        print(f"🍽️ Suggested {time_period} Food: {suggestion[0]}")

        # Get current timestamp in readable format
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_time = format_time_for_message(current_time)
        
        # Save data with timestamp and time period
        save_to_csv([name, number, location, weather, temperature, category, suggestion[0], current_time, time_period])
        
        show_popup_notification(f"🍽️ {time_period.capitalize()} Food Suggestion", 
                               f"{suggestion[0]} is perfect for {temperature}°C in {location}.")

        # Send immediate SMS with time period mention
        greeting = "Good morning" if time_period == "morning" else "Good afternoon" if time_period == "afternoon" else "Good evening"
        sms_message = f"🍽️ {greeting}, {name}! Here's your {time_period} food suggestion for {temperature}°C in {location}: {suggestion[0]} (sent at {formatted_time})"
        send_sms_notification(number, sms_message)
        
        # Schedule next day suggestion at the same time
        schedule_next_day_suggestion(name, number, location, current_time, food_type)
        print(f"📅 Next {time_period} suggestion scheduled for tomorrow at the same time!")

    except Exception as e:
        print("⚠️ Error:", e)

# === Schedule all time periods for a user ===
def schedule_all_time_periods(name, phone, location, food_type=None):
    """Schedule suggestions for morning, afternoon and evening for a user"""
    now = datetime.datetime.now()
    
    # Define a time for each period (using middle of the range)
    schedule_times = {
        "morning": "08:30",
        "afternoon": "13:30", 
        "evening": "19:30"
    }
    
    for period, time_str in schedule_times.items():
        # Create a timestamp for scheduling
        hour, minute = map(int, time_str.split(':'))
        schedule_dt = now.replace(hour=hour, minute=minute)
        timestamp = schedule_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Schedule for this period
        schedule_next_day_suggestion(name, phone, location, timestamp, food_type)
        
    print(f"✅ Scheduled user {name} for all time periods (morning, afternoon, evening)")

# === Find user's previous time periods ===
def get_user_time_periods(name, phone):
    """Find all unique time periods a user has received suggestions in"""
    dataset = read_csv()
    time_periods = set()
    
    for row in dataset:
        if row[0] == name and row[1] == phone:
            try:
                # Get timestamp and determine time period
                if len(row) > 8 and row[8]:  # If time period is stored
                    time_periods.add(row[8])
                else:  # Calculate from timestamp
                    suggestion_time = datetime.datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
                    time_periods.add(get_time_period(suggestion_time.hour))
            except Exception:
                pass
    
    return time_periods

# === Main startup function === 
def startup():
    try:
        # Start the scheduler in a background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Load existing users and schedule their suggestions
        dataset = read_csv()
        users_processed = set()
        user_schedules = {}  # Track all timestamps for each user
        
        # First, collect all timestamps by user
        for row in dataset:
            try:
                name, phone = row[0], row[1]
                user_key = (name, phone)
                
                if user_key not in user_schedules:
                    user_schedules[user_key] = []
                
                # Add this timestamp to the user
                if len(row) >= 8:  # Make sure timestamp exists
                    try:
                        timestamp = row[7]
                        # Extract time only
                        dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        time_only = dt.strftime("%H:%M")
                        
                        # Store time with other info
                        user_schedules[user_key].append({
                            'time': time_only,
                            'location': row[2],
                            'time_period': row[8] if len(row) > 8 else get_time_period(dt.hour)
                        })
                    except Exception:
                        pass
            except Exception as e:
                print(f"⚠️ Error processing row: {e}")
        
        # Now schedule each user with their unique times from each time period
        for user_key, timestamps in user_schedules.items():
            try:
                name, phone = user_key
                
                # Group by time period
                period_times = {"morning": [], "afternoon": [], "evening": []}
                
                for entry in timestamps:
                    period_times[entry['time_period']].append(entry)
                
                # For each time period, schedule the most recent time
                location = None  # Will be set from the data
                
                for period, entries in period_times.items():
                    if entries:
                        # Use the most recent entry for this period
                        entry = entries[-1]  # Assuming the data is in chronological order
                        location = entry['location']
                        
                        # Create a timestamp for scheduling
                        now = datetime.datetime.now()
                        hour, minute = map(int, entry['time'].split(':'))
                        schedule_dt = now.replace(hour=hour, minute=minute)
                        timestamp = schedule_dt.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Schedule this specific time
                        food_type = None  # Could be extracted from history if needed
                        schedule_next_day_suggestion(name, phone, location, timestamp, food_type)
                        
                        print(f"📆 Scheduled {period} suggestion for {name} at {entry['time']}")
                
                users_processed.add(user_key)
                
            except Exception as e:
                print(f"⚠️ Error scheduling user {user_key}: {e}")
        
        print(f"✅ Scheduled {len(users_processed)} users with time-specific suggestions")
        print("\n🌟 Food Suggester is running with time-based scheduling.")
        print("🔄 You can still use the interactive mode by calling interactive_food_suggester()")
        
    except Exception as e:
        print(f"⚠️ Startup error: {e}")

# === Main Block ===
if __name__ == "__main__":
    # Install required packages if not present
    try:
        import schedule
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "schedule", "plyer", "twilio", "requests"])
        import schedule
    
    # Start the application with automatic scheduling
    startup()
    
    # Run the interactive mode once at startup
    interactive_food_suggester()
