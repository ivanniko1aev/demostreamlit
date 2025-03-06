import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json
import os

print("\n=== Starting Data Processing Pipeline ===\n")

# Google Sheets API setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Try to get credentials from Streamlit secrets first (deployed environment)
try:
    if 'gcp_service_account' in st.secrets:
        creds_dict = dict(st.secrets['gcp_service_account'])
        # Convert private key from string to proper format
        if isinstance(creds_dict['private_key'], str):
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback to local creds.json (development environment)
        creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
except Exception as e:
    print(f"Error loading credentials: {e}")
    raise

client = gspread.authorize(creds)

# Fetch Attribution Data
print("Fetching attribution_data...")
sheet = client.open("Demo Data, StatSync").worksheet("attribution_data")
attribution_data = pd.DataFrame(sheet.get_all_records())
print(f"✓ Retrieved {len(attribution_data)} rows from attribution_data")
print("Sample Time Period values before parsing:", attribution_data["Time Period"].head().tolist())
print("Time Period range before parsing:", attribution_data["Time Period"].min(), "to", attribution_data["Time Period"].max())

# Parse Time Period with mixed formats
attribution_data["Time Period"] = pd.to_datetime(attribution_data["Time Period"], format="mixed", errors="coerce")
print("Sample Time Period values after parsing:", attribution_data["Time Period"].head().tolist())
print("Time Period range after parsing:", attribution_data["Time Period"].min(), "to", attribution_data["Time Period"].max())
print("Number of null values after parsing:", attribution_data["Time Period"].isna().sum())

attribution_data["Month"] = attribution_data["Time Period"].dt.strftime("%B")
attribution_data["YearMonth"] = attribution_data["Time Period"].dt.strftime("%b. %Y")
print("YearMonth range:", attribution_data["YearMonth"].min(), "to", attribution_data["YearMonth"].max())
print("Unique YearMonths:", sorted(attribution_data["YearMonth"].unique()))
numeric_cols = ["Inquiries", "Pricing Sent", "Orders", "Paid Orders", "Total Job Amount", "Campaign Cost", "Cost per Closed Sale"]
attribution_data[numeric_cols] = attribution_data[numeric_cols].apply(pd.to_numeric, errors="coerce").round(0)
attribution_data["Cost per Lead"] = (attribution_data["Campaign Cost"] / attribution_data["Inquiries"]).replace([float("inf"), -float("inf")], 0).fillna(0).round(0)
attribution_data["ROI_numeric"] = ((attribution_data["Total Job Amount"] - attribution_data["Campaign Cost"]) / 
                                   attribution_data["Campaign Cost"]).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)
attribution_data["ROI"] = attribution_data["ROI_numeric"].apply(lambda x: f"{int(x * 100)}%")
attribution_data["Display Source"] = attribution_data.apply(
    lambda row: row["Source"] if row["Campaign Name"] == "N/A" else row["Campaign Name"], axis=1)

# Fetch Orders Data
print("\nFetching orders_data...")
orders_sheet = client.open("Demo Data, StatSync").worksheet("orders_data")
orders_data = pd.DataFrame(orders_sheet.get_all_records())
print(f"✓ Retrieved {len(orders_data)} rows from orders_data")
print("Sample timeslot datetime values before parsing:", orders_data["timeslot datetime"].head().tolist())

# Parse timeslot datetime with mixed formats
orders_data["timeslot datetime"] = pd.to_datetime(orders_data["timeslot datetime"], format="mixed", errors="coerce")
print("Sample timeslot datetime values after parsing:", orders_data["timeslot datetime"].head().tolist())
print("Number of null values after parsing:", orders_data["timeslot datetime"].isna().sum())

orders_data["Month"] = orders_data["timeslot datetime"].dt.strftime("%B")
orders_data["YearMonth"] = orders_data["timeslot datetime"].dt.strftime("%b. %Y")
orders_data[["Services price", "discount amount"]] = orders_data[["Services price", "discount amount"]].apply(pd.to_numeric, errors="coerce").fillna(0)
orders_data["Order Total"] = (orders_data["Services price"] - orders_data["discount amount"]).round(0)
orders_data = orders_data[orders_data["status"] != "CANCELLED"]
orders_data = orders_data[orders_data["timeslot datetime"].dt.year >= 2020]

# After processing orders data
print("\nOrders Data Date Range:")
print("Orders date range:", orders_data["timeslot datetime"].min(), "to", orders_data["timeslot datetime"].max())
print("Orders YearMonth range:", orders_data["YearMonth"].min(), "to", orders_data["YearMonth"].max())
print("Unique Orders YearMonths:", sorted(orders_data["YearMonth"].unique()))

# Fetch Notifications Data
print("\nFetching notifications_data...")
notifications_sheet = client.open("Demo Data, StatSync").worksheet("notifications_data")
notifications_data = pd.DataFrame(notifications_sheet.get_all_records())
print(f"✓ Retrieved {len(notifications_data)} rows from notifications_data")
print("Sample datetime sent values before parsing:", notifications_data["datetime sent"].head().tolist())

# Parse datetime sent with mixed formats
notifications_data["datetime sent"] = pd.to_datetime(notifications_data["datetime sent"], format="mixed", errors="coerce")
print("Sample datetime sent values after parsing:", notifications_data["datetime sent"].head().tolist())
print("Number of null values after parsing:", notifications_data["datetime sent"].isna().sum())

notifications_data["YearMonth"] = notifications_data["datetime sent"].dt.strftime("%b. %Y")
# Filter for relevant notification events
notifications_data = notifications_data[notifications_data["Notification event"].isin(["send_dashboard", "estimates_sent"])]
# Remove duplicates based on customer id within each month
notifications_data = notifications_data.drop_duplicates(subset=["Customer id", "YearMonth"])
# Group by YearMonth to get unique Pricing Sent counts
pricing_sent_data = notifications_data.groupby("YearMonth").size().reset_index(name="Pricing Sent")

# After processing notifications data
print("\nNotifications Data Date Range:")
print("Notifications date range:", notifications_data["datetime sent"].min(), "to", notifications_data["datetime sent"].max())
print("Notifications YearMonth range:", notifications_data["YearMonth"].min(), "to", notifications_data["YearMonth"].max())
print("Unique Notifications YearMonths:", sorted(notifications_data["YearMonth"].unique()))

print("\n=== Data Processing Summary ===")
print("Attribution Data Shape:", attribution_data.shape)
print("Orders Data Shape:", orders_data.shape)
print("Notifications Data Shape:", notifications_data.shape)
print("Pricing Sent Data Shape:", pricing_sent_data.shape)

print("\n=== Data Processing Complete ===\n")