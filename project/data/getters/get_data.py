import pandas as pd
from sodapy import Socrata
from dotenv import load_dotenv, set_key
import os
from time import sleep

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
APP_TOKEN = os.getenv("APP_TOKEN")
SOCRATA_USERNAME = os.getenv("SOCRATA_USERNAME")
SOCRATA_PASSWORD = os.getenv("SOCRATA_PASSWORD")
OFFSET = int(os.getenv("OFFSET", 0))  # Default offset is 0 if not set

# Initialize Socrata client
client = Socrata(domain="data.cityofnewyork.us",
                 app_token=APP_TOKEN,
                 username=SOCRATA_USERNAME,
                 password=SOCRATA_PASSWORD)

MAX_RETRIES = 100
RETRY_AFTER = 30

# Dataset ID and output directory
DATASET_ID = "u253-aew4"
OUTPUT_DIR = "batches/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Pagination parameters
LIMIT = 100000

# Columns and mapping
FEE_COLS = ['base_passenger_fare', 'tolls', 'bcf', 'sales_tax', 'congestion_surcharge', 'airport_fee']
DROP_COLS = ['dispatching_base_num', 'originating_base_num', 'on_scene_datetime', 'tips', 'shared_request_flag',
             'shared_match_flag', 'access_a_ride_flag', 'wav_request_flag', 'wav_match_flag', 'base_passenger_fare',
             'tolls', 'bcf', 'sales_tax', 'congestion_surcharge', 'airport_fee', 'hvfhs_license_num', 'driver_pay']
LICENSE_MAP = {
    "HV0002": "Juno",
    "HV0003": "Uber",
    "HV0004": "Via",
    "HV0005": "Lyft"
}
DATETIME_COLS = ["request_datetime", "pickup_datetime", "dropoff_datetime"]
NUMERIC_COLS = ["pulocationid", "dolocationid", "trip_miles", "trip_time"]

def process_batch(results):
    # Convert to pandas DataFrame
    df = pd.DataFrame.from_records(results)

    # Add new column 'fee' as the sum of the FEE_COLS
    df['fee'] = df[FEE_COLS].apply(pd.to_numeric, errors='coerce').sum(axis=1)

    # Replace the values in 'hvfhs_license_num' and rename the column
    df['hvfhs'] = pd.Categorical(df['hvfhs_license_num'].replace(LICENSE_MAP))

    # Convert datetime columns
    for col in DATETIME_COLS:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Convert numeric columns
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop the specified columns
    df.drop(columns=DROP_COLS, inplace=True)

    return df

def download_and_save_batches():
    offset = OFFSET
    total_rows = 0

    try:
        while True:
            # Fetch data from the API
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"\033[KRows {offset} to {offset + LIMIT}: Fetching (Attempt {attempt + 1}/{MAX_RETRIES})...", end='\r')
                    results = client.get(DATASET_ID, limit=LIMIT, offset=offset)
                    break
                except Exception as e:
                    if attempt + 1 < MAX_RETRIES:
                        for j in range(RETRY_AFTER, 0, -1):
                            print(f"\033[KRows {offset} to {offset + LIMIT}: Error fetching: \"{e}\" Retrying after {j} seconds (Attempt {attempt + 1}/{MAX_RETRIES}).", end='\r')
                            sleep(1)
                    else:
                        print(f"\033[KRows {offset} to {offset + LIMIT}: Error fetching: \"{e}\" Max retries reached. Exiting.")
                        break

            if not results:
                print(f"\033[KRows {offset} to {offset + LIMIT}: No more data to fetch.")
                break

            print(f"\033[KRows {offset} to {offset + LIMIT}: Processing...", end='\r')

            # Process batch
            batch_df = process_batch(results)

            # Save batch to .pkl file
            output_file = os.path.join(OUTPUT_DIR, f"batch_{offset}_{offset + len(batch_df)}.pkl")
            batch_df.to_pickle(output_file)

            print(f"\033[KRows {offset} to {offset + LIMIT}: Saved to {output_file}", end='\r')

            # Update tracking
            total_rows += len(batch_df)
            offset += LIMIT
            update_offset_in_env(offset)

    except Exception as e:
        print(f"\033[KAn error occurred: {e}")

    print(f"\033[KData download complete. Total rows downloaded: {total_rows}")

def update_offset_in_env(offset):
    """
    Update the OFFSET value in the .env file.
    """
    set_key('.env', 'OFFSET', str(offset))

# Run the download
if __name__ == "__main__":
    download_and_save_batches()
