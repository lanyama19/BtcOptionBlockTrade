import os
import json
import re
import pandas as pd
from collections import Counter
from datetime import datetime


file_path = os.path.join(os.getcwd(), "data", "result.json")

# Read the JSON file
try:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)["messages"]  # Load JSON data into a Python object
except FileNotFoundError:
    print(f"The file {file_path} does not exist. Please check the path.")
except json.JSONDecodeError:
    print(f"The file {file_path} is not in a valid JSON format.")

processed_data = []
for record in data:
    # Extract the required fields
    if all(key in record for key in ["id", "date", "date_unixtime", "text"]):
        new_record = {
            "id": record["id"],
            "date": record["date"],
            "date_unixtime": record["date_unixtime"],
            "text": record["text"]
        }
        processed_data.append(new_record)


# New empty list for the final results
trade_aggregated = []

# Initialize number_counts
number_counts = 0

# Loop through each record in processed_data in reverse order with index
for idx, record in enumerate(reversed(processed_data)):
    # Debugging information
    print(f"Processing Record Index: {len(processed_data) - 1 - idx}, ID: {record.get('id', 'Unknown')}")

    # Check if "text" field is valid
    if record.get("text", "") == '':
        print("Skipping record: 'text' is empty.")
        continue
    if isinstance(record.get("text", ""), dict):
        print("Skipping record: 'text' is a dictionary.")
        continue
    if isinstance(record.get("text", "")[0], dict):
        print("Skipping record: 'text' is a dictionary.")
        continue

    # Extract and process "text" with exception handling
    try:
        text_field = record.get("text", "")
        if isinstance(text_field, list):
            text = text_field[0].strip() if text_field else ''
        else:
            text = text_field.strip()

        if not text:  # Check if text is still empty after processing
            print("Skipping record: 'text' is empty after processing.")
            continue
    except IndexError:
        print("Skipping record: 'text' is not iterable.")
        continue
    except AttributeError:
        print("Skipping record: 'text' does not support strip().")
        continue

    first_line = text.split("\n")[0]  # Extract the first line

    # Skip records if the first line contains "FUTURES"
    if "FUTURES" in first_line:
        print("Skipping record: 'FUTURES' found in first line.")
        continue

    # Check if "BTC" exists and if "Sold" or "Bought" exists
    if not re.search(r"BTC", text, re.IGNORECASE) or not re.search(r"(Sold|Bought)", text, re.IGNORECASE):
        print("Skipping record: 'BTC' or 'Sold/Bought' not found.")
        continue

    # Prepare shared fields for each record
    record_id = record["id"]
    record_date = record["date"]
    record_date_unixtime = record["date_unixtime"]

    # Extract "contract_size" from the first line
    contract_size_match = re.search(r"\(x([\d.]+)\)", first_line)
    contract_size = float(contract_size_match.group(1)) if contract_size_match else None

    # Extract actions (Sold/Bought)
    action_matches = re.findall(r"(?<!Total\s)(Sold|Bought)", text, re.IGNORECASE)

    # Extract contract names
    contract_name_matches = re.findall(r"BTC-\w+-\d+-[CP]", text)

    # Extract premiums
    premium_matches = re.findall(r"at.*?\(\$(.*?)\)", text)

    # Extract IVs
    iv_matches = re.findall(r"IV\s*:\s*([\d.]+)%", text)

    # Extract Index Price (allow optional spaces between "Index Price" and "$")
    index_price_match = re.search(r"Index Price\s*\$([\d.]+)", text)
    index_price = float(index_price_match.group(1)) if index_price_match else None

    # Count the number of Sold/Bought matches
    sold_bought_count = len(action_matches)
    number_counts = number_counts + sold_bought_count  # Increment the total count

    # Debugging: print the updated number_counts
    print(f"Total Sold/Bought count so far: {number_counts}")

    # Ensure all extracted fields have the same number of matches
    num_matches = min(len(action_matches), len(contract_name_matches), len(premium_matches), len(iv_matches))

    for i in range(num_matches):
        action = action_matches[i]
        contract_name = contract_name_matches[i]
        premium = premium_matches[i]
        iv = float(iv_matches[i])

        # Append the result
        trade_aggregated.append({
            "id": record_id,
            "index": len(processed_data) - 1 - idx,
            "date": record_date,
            "date_unixtime": record_date_unixtime,
            "contract_size": contract_size,
            "action": action,
            "contract_name": contract_name,
            "iv": iv,
            "premium": premium,
            "index_price": index_price
        })


# Convert to DataFrame
df = pd.DataFrame(trade_aggregated)

# Function to convert premium to float and handle 'K'/'M'
def convert_premium(value):
    if isinstance(value, str):
        if 'K' in value:
            return float(value.replace('K', '')) * 1000
        elif 'M' in value:
            return float(value.replace('M', '')) * 1000000
        else:
            return float(value)
    return value

# Convert columns to float
df["contract_size"] = df["contract_size"].astype(float)
df["iv"] = df["iv"].astype(float)
df["index_price"] = df["index_price"].astype(float)
df["premium"] = df["premium"].apply(convert_premium)


# Function to extract expiry, strike, and type from contract_name
def extract_details(contract_name):
    # Updated regex to handle single or double-digit days
    match = re.match(r".*-(\d{1,2}[A-Z]{3}\d{2})-(\d+)-([CP])", contract_name)
    if match:
        # Extract expiry in format like "5DEC24" or "15JAN25"
        expiry_str = match.group(1)
        # Convert to datetime, assuming day first
        expiry = datetime.strptime(expiry_str, "%d%b%y")
        # Extract strike price
        strike = float(match.group(2))
        # Extract option type
        option_type = "Call" if match.group(3) == "C" else "Put"
        return expiry, strike, option_type
    return None, None, None

# Apply the function to the DataFrame
df[["expiry", "strike", "type"]] = df["contract_name"].apply(
    lambda x: pd.Series(extract_details(x))
)

df['expiry'] = df['expiry'].apply(lambda x: x + pd.Timedelta(hours=8) if pd.notna(x) else x)
# Convert date_unixtime to datetime
df['current_date'] = pd.to_datetime(df['date_unixtime'], unit='s')

# Calculate time to maturity in years
df['time_to_maturity'] = df.apply(
    lambda row: (row['expiry'] - row['current_date']).total_seconds() / (365 * 24 * 60 * 60)
    if pd.notna(row['expiry']) and pd.notna(row['current_date']) else None,
    axis=1
)

#Set 'risk_free_rate to 0.0
df['risk_free_rate'] = 0.0

# Save as pickle file
df.to_pickle("block_trade.pkl")