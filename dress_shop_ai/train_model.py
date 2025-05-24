import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from datetime import datetime, timedelta

# Load and preprocess the dataset
df = pd.read_csv('data.csv')

# Convert Date column to datetime and extract features
df['Date'] = pd.to_datetime(df['Date'])
df['Month'] = df['Date'].dt.month
df['DayOfWeek'] = df['Date'].dt.dayofweek
df['Year'] = df['Date'].dt.year
df['DayOfMonth'] = df['Date'].dt.day
df['Season'] = pd.cut(df['Month'], 
    bins=[0,3,6,9,12], 
    labels=['Winter', 'Spring', 'Summer', 'Fall'])

# Calculate rolling averages for seasonal trends
df['MA7_Quantity'] = df.groupby(['Quality', 'Composition'])['Quantity'].transform(
    lambda x: x.rolling(window=7, min_periods=1).mean())
df['MA30_Quantity'] = df.groupby(['Quality', 'Composition'])['Quantity'].transform(
    lambda x: x.rolling(window=30, min_periods=1).mean())

# Clean Composition column
df['Composition'] = df['Composition'].str.replace('100% ', '')

# Encode categorical columns
label_cols = ['Agent', 'Customer', 'Quality', 'Weave', 'Composition', 'Season']
encoders = {}
for col in label_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le

# Define features and target
features = ['Year', 'Month', 'DayOfMonth', 'DayOfWeek', 'Agent', 
           'Quality', 'Weave', 'Composition', 'MA7_Quantity', 'MA30_Quantity']
X = df[features]
y = df['Quantity']

# Split the data chronologically
train_size = int(len(df) * 0.8)
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Train the model
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)
model.fit(X_train, y_train)

# Evaluate the model
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("Model Performance:")
print(f"Mean Squared Error: {mse:.2f}")
print(f"R² Score: {r2:.2f}")

# Save the model and encoders
with open('model.pkl', 'wb') as f:
    joblib.dump(model, f, protocol=4)
with open('encoders.pkl', 'wb') as f:
    joblib.dump(encoders, f, protocol=4)

print("\n✅ Model and encoders saved successfully.")
