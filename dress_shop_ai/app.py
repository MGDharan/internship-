import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import pandas as pd
import joblib
import datetime
import requests

# Load environment variables
load_dotenv()

print("Loaded Gemini API Key:", os.getenv('GEMINI_API_KEY'))

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session support

# Load model and encoders
model = joblib.load('model.pkl')
encoders = joblib.load('encoders.pkl')

# Load dataset for context
df = pd.read_csv('data.csv')

# Gemini API call function

def call_gemini_api(user_input, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": user_input
                    }
                ]
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        try:
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return "Sorry, I couldn't understand the response from Gemini."
    else:
        return f"Error: {response.status_code} - {response.text}"

@app.route('/')
def index():
    if 'messages' not in session:
        session['messages'] = []
    return render_template('index.html', messages=session['messages'])

@app.route('/predict', methods=['POST'])
def predict():
    # Initialize variables outside try block
    response = ""
    chart_data = None
    sales_data = None
    sales_date = None
    best_seller = None
    date_found = None

    try:
        api_key = os.getenv('GEMINI_API_KEY')
        user_input = request.form['user_input']
        
        # Check for date in user input
        for word in user_input.split():
            try:
                date = pd.to_datetime(word)
                date_found = date
                break
            except:
                continue

        # New: Suggest best dress for a given day by analyzing all previous years
        if date_found and ("which dress" in user_input.lower() or "best seller" in user_input.lower() or "most number" in user_input.lower()):
            # Get all sales for the same month and day across all years
            day_data = df[(pd.to_datetime(df['Date']).dt.month == date_found.month) & (pd.to_datetime(df['Date']).dt.day == date_found.day)]
            if not day_data.empty:
                # Group by Quality, Weave, Composition, sum Quantity
                group = day_data.groupby(['Quality', 'Weave', 'Composition'])['Quantity'].sum()
                best = group.idxmax()
                best_qty = group.max()
                best_name = f"{best[0]} {best[1]} {best[2]}"
                suggested_stock = int(best_qty * 1.2)  # 20% safety margin
                response = (
                    f"Based on previous years' data for {date_found.strftime('%B %d')}, "
                    f"the best-selling dress is **{best_name}** with a total of **{best_qty} units** sold.\n\n"
                    f"Suggestion: The owner should stock up at least **{suggested_stock} units** of {best_name} for this day (including a 20% safety margin)!"
                )
            else:
                response = f"No historical sales data available for {date_found.strftime('%B %d')}."
            return jsonify({'response': response, 'chart_data': None, 'sales_data': None, 'sales_date': None, 'best_seller': None})

        # Check for date or sales-related queries
        date_found = None
        for word in user_input.split():
            try:
                date = pd.to_datetime(word)
                date_found = date
                break
            except Exception:
                continue

        if date_found:
            # Get data for the same day from both 2022 and 2023
            sales_2022 = df[
                (pd.to_datetime(df['Date']).dt.month == date_found.month) &
                (pd.to_datetime(df['Date']).dt.day == date_found.day) &
                (pd.to_datetime(df['Date']).dt.year == 2022)
            ]
            
            sales_2023 = df[
                (pd.to_datetime(df['Date']).dt.month == date_found.month) &
                (pd.to_datetime(df['Date']).dt.day == date_found.day) &
                (pd.to_datetime(df['Date']).dt.year == 2023)
            ]

            # Prepare comparison data
            sales_distribution = {
                '2022': {},
                '2023': {}
            }

            for year, data in [('2022', sales_2022), ('2023', sales_2023)]:
                for quality in ['Premium', 'Standard']:
                    for composition in ['Cotton', 'Silk']:
                        key = f"{quality} {composition}"
                        sales_distribution[year][key] = int(data[
                            (data['Quality'] == quality) & 
                            (data['Composition'].str.contains(composition))
                        ]['Quantity'].sum())

            # Create chart data for comparison
            chart_data = {
                'labels': list(sales_distribution['2022'].keys()),
                'datasets': [
                    {
                        'label': '2022',
                        'data': list(sales_distribution['2022'].values()),
                        'backgroundColor': ['rgba(255, 99, 132, 0.5)', 'rgba(54, 162, 235, 0.5)', 
                                          'rgba(255, 206, 86, 0.5)', 'rgba(75, 192, 192, 0.5)'],
                        'borderColor': ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
                                      'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)'],
                        'borderWidth': 1
                    },
                    {
                        'label': '2023',
                        'data': list(sales_distribution['2023'].values()),
                        'backgroundColor': ['rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)',
                                          'rgba(255, 206, 86, 0.8)', 'rgba(75, 192, 192, 0.8)'],
                        'borderColor': ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
                                      'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)'],
                        'borderWidth': 1
                    }
                ]
            }

            # Calculate best sellers for both years
            best_seller_2022 = max(sales_distribution['2022'].items(), key=lambda x: x[1])[0] if sales_distribution['2022'] else None
            best_seller_2023 = max(sales_distribution['2023'].items(), key=lambda x: x[1])[0] if sales_distribution['2023'] else None

            return jsonify({
                'response': f"Comparing sales for {date_found.strftime('%B %d')} between 2022 and 2023",
                'chart_data': chart_data,
                'sales_data': sales_distribution,
                'sales_date': date_found.strftime('%B %d'),
                'best_seller': {'2022': best_seller_2022, '2023': best_seller_2023}
            })

        elif date_found or 'stock' in user_input.lower() or 'should i sell' in user_input.lower():
            # Get sales data for the specific date if provided
            if date_found:
                current_data = df[pd.to_datetime(df['Date']).dt.date == date_found.date()]
                sales_distribution = {}
                for quality in ['Premium', 'Standard']:
                    for composition in ['Cotton', 'Silk']:
                        key = f"{quality} {composition}"
                        sales_distribution[key] = int(current_data[
                            (current_data['Quality'].str.lower() == quality.lower()) &
                            (current_data['Composition'].str.lower().str.contains(composition.lower()))
                        ]['Quantity'].sum())
                if sum(sales_distribution.values()) == 0:
                    # If no data for the day, fallback to month
                    current_data = df[pd.to_datetime(df['Date']).dt.month == date_found.month]
                    for quality in ['Premium', 'Standard']:
                        for composition in ['Cotton', 'Silk']:
                            key = f"{quality} {composition}"
                            sales_distribution[key] = int(current_data[
                                (current_data['Quality'].str.lower() == quality.lower()) &
                                (current_data['Composition'].str.lower().str.contains(composition.lower()))
                            ]['Quantity'].sum())
                best_seller = max(sales_distribution.items(), key=lambda x: x[1])[0] if sales_distribution else None
                chart_data = {
                    'labels': list(sales_distribution.keys()),
                    'datasets': [{
                        'data': list(sales_distribution.values()),
                        'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                        'borderColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                        'borderWidth': 1
                    }]
                }
                response = f"Based on historical data, here's the sales analysis for {date_found.strftime('%B %d, %Y')}:\n\n🏆 Best-seller: {best_seller}\n📊 Sales Distribution:\n"
                for dress, quantity in sales_distribution.items():
                    response += f"- {dress}: {quantity} units\n"
                sales_data = sales_distribution
                sales_date = date_found.strftime('%B %d, %Y')
                return jsonify({
                    'response': response,
                    'chart_data': chart_data,
                    'sales_data': sales_data,
                    'sales_date': sales_date,
                    'best_seller': best_seller
                })
            else:
                # If no date was found, use current month data
                current_month = pd.Timestamp.now().month
                current_data = df[pd.to_datetime(df['Date']).dt.month == current_month]
                sales_distribution = {}
                for quality in ['Premium', 'Standard']:
                    for composition in ['Cotton', 'Silk']:
                        key = f"{quality} {composition}"
                        sales_distribution[key] = int(current_data[
                            (current_data['Quality'] == quality) & 
                            (current_data['Composition'].str.contains(composition))
                        ]['Quantity'].sum())
                best_seller = max(sales_distribution.items(), key=lambda x: x[1])[0]
                chart_data = {
                    'labels': list(sales_distribution.keys()),
                    'datasets': [{
                        'data': list(sales_distribution.values()),
                        'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                        'borderColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                        'borderWidth': 1
                    }]
                }
                response = f"Based on current month data, here's the sales analysis for {pd.Timestamp.now().strftime('%B %Y')}:\n\n🏆 Best-seller: {best_seller}\n📊 Sales Distribution:\n"
                for dress, quantity in sales_distribution.items():
                    response += f"- {dress}: {quantity} units\n"
                sales_data = sales_distribution
                sales_date = pd.Timestamp.now().strftime('%B %Y')
                return jsonify({
                    'response': response,
                    'chart_data': chart_data,
                    'sales_data': sales_data,
                    'sales_date': sales_date,
                    'best_seller': best_seller
                })
        else:
            # Direct price and amount logic for owner queries
            user_input_lower = user_input.lower()
            dress_catalog = [
                {
                    'name': 'Premium Cotton Plain',
                    'keywords': ['cotton', 'plain'],
                    'price': '₹490',
                    'composition': '100% Cotton',
                    'quality': 'Premium'
                },
                {
                    'name': 'Standard Silk Satin',
                    'keywords': ['silk', 'satin', 'standard'],
                    'price': '₹199',
                    'composition': '100% Silk',
                    'quality': 'Standard'
                },
                {
                    'name': 'Premium Silk Satin',
                    'keywords': ['silk', 'satin', 'premium'],
                    'price': '₹225',
                    'composition': '100% Silk',
                    'quality': 'Premium'
                }
            ]
            for dress in dress_catalog:
                if 'price' in user_input_lower and any(k in user_input_lower for k in dress['keywords']):
                    # Find total sold for this dress
                    mask = (
                        (df['Quality'].str.lower() == dress['quality'].lower()) &
                        (df['Composition'].str.lower() == dress['composition'].lower())
                    )
                    total_sold = df[mask]['Quantity'].sum()
                    response = f"The price of {dress['name']} is {dress['price']}. Total sold: {total_sold} units."
                    return jsonify({'response': response, 'chart_data': None, 'sales_data': None, 'sales_date': None, 'best_seller': None})
            # General chat/AI assistant
            context = (
                "You are a fun and witty AI assistant in a dress shop. "
                "Your job is to answer questions about dress sales and collections. "
                "You are a dress shop assistant and owner of the shop. "
                "You may share the sales data and other information about the shop and the dresses about owner, "
                "basically you are working for the owner of the shop to show all the information about customers and sales data. "
                f"Here is a summary of the sales data:\n"
                f"Customers: {', '.join(df['Customer'].unique()) if 'Customer' in df.columns else 'N/A'}\n"
                f"Top customer: {df.groupby('Customer')['Quantity'].sum().idxmax() if 'Customer' in df.columns else 'N/A'}\n"
            )
            full_prompt = f"{context}\n\nUser: {user_input}"
            response = call_gemini_api(full_prompt, api_key)
            return jsonify({'response': response, 'chart_data': None, 'sales_data': None, 'sales_date': None, 'best_seller': None})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'response': f'Error occurred: {e}',
            'chart_data': None,
            'sales_data': None,
            'sales_date': None,
            'best_seller': None
        }), 500

@app.route('/update_chart')
def update_chart():
    try:
        date_str = request.args.get('date')
        group_by = request.args.get('group_by', 'Agent')  # Default to Agent
        if not date_str:
            return jsonify({'error': 'Date parameter is required'}), 400
        selected_date = pd.to_datetime(date_str)
        selected_data = df[pd.to_datetime(df['Date']).dt.month == selected_date.month]
        if selected_data.empty:
            return jsonify({'error': 'No data available for selected month'}), 404

        # Group by the selected field
        if group_by not in selected_data.columns:
            return jsonify({'error': f'Invalid group_by: {group_by}'}), 400

        sales_distribution = selected_data.groupby(group_by)['Quantity'].sum().to_dict()
        best_seller = max(sales_distribution.items(), key=lambda x: x[1])[0]
        has_sales = any(sales_distribution.values())
        response_data = {
            'message': {
                'date': selected_date.strftime('%B %d, %Y'),
                'best_seller': best_seller if has_sales else 'No sales data available',
                'sales_details': [
                    {'dress_type': k, 'quantity': v}
                    for k, v in sales_distribution.items()
                ] if has_sales else []
            },
            'chart_data': {
                'labels': list(sales_distribution.keys()),
                'datasets': [{
                    'data': list(sales_distribution.values()),
                    'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                    'borderColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                    'borderWidth': 1
                }]
            }
        }
        if not has_sales:
            response_data['message']['status'] = 'No historical sales data available for this date'
            response_data['chart_data'] = None
        return jsonify(response_data)
    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        print(f"Error in update_chart: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard')
def dashboard():
    # Show the current month's sales data
    current_month = pd.Timestamp.now().month
    current_data = df[pd.to_datetime(df['Date']).dt.month == current_month]
    
    # Calculate sales by agent and quality
    sales_distribution = {}
    for agent in ['Sammy', 'Mark']:
        for quality in ['Premium', 'Standard']:
            key = f"{agent}'s {quality}"
            sales_distribution[key] = int(current_data[
                (current_data['Agent'] == agent) & 
                (current_data['Quality'] == quality)
            ]['Quantity'].sum())
    
    # If no data for current month, use the most recent month's data
    if sum(sales_distribution.values()) == 0:
        latest_date = pd.to_datetime(df['Date']).max()
        current_data = df[pd.to_datetime(df['Date']).dt.month == latest_date.month]
        for agent in ['Sammy', 'Mark']:
            for quality in ['Premium', 'Standard']:
                key = f"{agent}'s {quality}"
                sales_distribution[key] = int(current_data[
                    (current_data['Agent'] == agent) & 
                    (current_data['Quality'] == quality)
                ]['Quantity'].sum())
    
    best_seller = max(sales_distribution.items(), key=lambda x: x[1])[0]
    
    chart_data = {
        'labels': list(sales_distribution.keys()),
        'datasets': [{
            'data': list(sales_distribution.values()),
            'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
            'borderColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
            'borderWidth': 1
        }]
    }
    
    if not current_data.empty:
        display_date = pd.to_datetime(current_data['Date'].iloc[0]).strftime('%Y-%m')
    else:
        display_date = pd.Timestamp.now().strftime('%Y-%m')
    
    return render_template(
        'dashboard.html',
                          chart_data=chart_data,
                          sales_data=sales_distribution,
                          sales_date=display_date,
        best_seller=best_seller
    )

if __name__ == '__main__':
    app.run(debug=True)
