import pandas as pd
import os
from datetime import datetime

# Folder where AirDrop puts files
DOWNLOADS_FOLDER = os.path.expanduser("~/Downloads")
# DATA_DIR should be relative to the script location or absolute path
# Let's use the same robust logic we used in the other scripts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def process_phone_data():
    print("🔍 Scanning Downloads for Pickup CSV...")
    
    try:
        # Find files that contain "Pickup" (OffScreen export)
        files = [f for f in os.listdir(DOWNLOADS_FOLDER) if "Pickup" in f and f.endswith(".csv")]
        
        if not files:
            print("❌ No 'Pickup.csv' found. Please AirDrop the export first.")
            return

        # Get the most recent one
        latest_file = max([os.path.join(DOWNLOADS_FOLDER, f) for f in files], key=os.path.getctime)
        print(f"Processing: {os.path.basename(latest_file)}")

        df = pd.read_csv(latest_file)
        
        # 1. Convert Text to Datetime objects
        df['start'] = pd.to_datetime(df['start'])
        df['end'] = pd.to_datetime(df['end'])
        
        # 2. Calculate Duration in Minutes
        df['phone_minutes'] = (df['end'] - df['start']).dt.total_seconds() / 60
        
        # 3. Rename 'start' to 'timestamp'
        df.rename(columns={'start': 'timestamp'}, inplace=True)
        
        # 4. Save
        df_clean = df[['timestamp', 'phone_minutes']]
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        output_path = os.path.join(DATA_DIR, "phone_data_clean.csv")
        df_clean.to_csv(output_path, index=False)
        print(f"✅ Success! Saved {len(df_clean)} phone sessions to {output_path}")
        print("   (You can now run etl_pipeline.py)")
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")

if __name__ == "__main__":
    process_phone_data()