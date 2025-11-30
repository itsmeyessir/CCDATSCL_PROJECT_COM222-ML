import pandas as pd
import os
from datetime import datetime

# Folder where AirDrop puts files
DOWNLOADS_FOLDER = os.path.expanduser("~/Downloads")

# Project Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "phone_data_clean.csv")

def process_phone_data():
    print("🔍 Scanning Downloads for Pickup CSV...")
    
    try:
        files = [f for f in os.listdir(DOWNLOADS_FOLDER) if "Pickup" in f and f.endswith(".csv")]
        
        if not files:
            print("❌ No 'Pickup.csv' found. Please AirDrop the export first.")
            return

        # Get the most recent export
        latest_file = max([os.path.join(DOWNLOADS_FOLDER, f) for f in files], key=os.path.getctime)
        print(f"Processing: {os.path.basename(latest_file)}")

        # 1. Load New Data
        new_df = pd.read_csv(latest_file)
        new_df['start'] = pd.to_datetime(new_df['start'])
        new_df['end'] = pd.to_datetime(new_df['end'])
        new_df['phone_minutes'] = (new_df['end'] - new_df['start']).dt.total_seconds() / 60
        new_df.rename(columns={'start': 'timestamp'}, inplace=True)
        new_df = new_df[['timestamp', 'phone_minutes']] 

        # 2. Load Existing Data (Merge)
        if os.path.exists(OUTPUT_FILE):
            print(f"   Found existing data at {OUTPUT_FILE}. Merging...")
            existing_df = pd.read_csv(OUTPUT_FILE)
            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
            
            combined_df = pd.concat([existing_df, new_df])
            # Deduplicate based on timestamp
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='first')
        else:
            combined_df = new_df

        # 3. Save
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        combined_df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Success! Total records: {len(combined_df)} saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")

if __name__ == "__main__":
    process_phone_data()