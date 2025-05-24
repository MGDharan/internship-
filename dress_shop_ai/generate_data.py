import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)

# Generate dates for 2 years
start_date = datetime(2022, 1, 1)
end_date = datetime(2023, 12, 31)
dates = pd.date_range(start=start_date, end=end_date, freq='D')

# Define possible values
agents = ['Sammy', 'Mark']
customers = ['Mike Wilson', 'Sarah Johnson', 'David Lee', 'Emma Brown', 'James Smith']
qualities = ['Premium', 'Standard']
weaves = ['Plain', 'Satin']
compositions = ['100% Cotton', '100% Silk']

# Generate random data
n_records = len(dates) * 3  # Average 3 sales per day
data = {
    'Date': np.random.choice(dates, n_records),
    'Agent': np.random.choice(agents, n_records),
    'Customer': np.random.choice(customers, n_records),
    'Quality': np.random.choice(qualities, n_records),
    'Weave': np.random.choice(weaves, n_records),
    'Composition': np.random.choice(compositions, n_records)
}

# Add seasonal variations and trends
def generate_quantity(date, quality, composition):
    # Convert numpy.datetime64 to pandas Timestamp
    date = pd.Timestamp(date)
    
    # Base quantity
    base = np.random.randint(1, 5)
    
    # Seasonal factor (higher in wedding seasons: Feb-March and Oct-Nov)
    month = date.month
    if month in [2, 3, 10, 11]:
        base *= 1.5
    
    # Premium items tend to sell less but steadily
    if quality == 'Premium':
        base *= 0.7
    
    # Cotton sells more in summer, Silk in winter
    if composition == '100% Cotton' and month in [4, 5, 6, 7]:
        base *= 1.3
    elif composition == '100% Silk' and month in [11, 12, 1, 2]:
        base *= 1.3
    
    return int(max(1, base))

# Generate quantities with patterns
data['Quantity'] = [generate_quantity(date, quality, comp) 
                   for date, quality, comp in zip(data['Date'], data['Quality'], data['Composition'])]

# Create DataFrame and sort by date
df = pd.DataFrame(data)
df = df.sort_values('Date')

# Save to CSV
df.to_csv('data.csv', index=False)

print("Generated 2 years of sales data with the following statistics:")
print("\nTotal number of records:", len(df))
print("\nSales by Agent:")
print(df.groupby('Agent')['Quantity'].sum())
print("\nSales by Quality:")
print(df.groupby('Quality')['Quantity'].sum())
print("\nSales by Composition:")
print(df.groupby('Composition')['Quantity'].sum())