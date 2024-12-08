import pandas as pd
import os
import geopandas as gpd
from tqdm import tqdm


# Directory containing the .pkl files
INPUT_DIR = "batches/"
OUTPUT_DIR = "/"


def combine_batches(input_dir, valid_locations):
    # List all .pkl files in the directory
    files = [f for f in os.listdir(input_dir) if f.endswith('.pkl')]

    # Initialize an empty DataFrame
    combined_df = pd.DataFrame()

    for file in tqdm(files, desc="Processing files"):
        # Read each .pkl file into a DataFrame
        file_path = os.path.join(input_dir, file)
        batch_df = pd.read_pickle(file_path)

        # Filter by valid locations
        batch_df = batch_df.loc[
            batch_df["pulocationid"].isin(valid_locations) &
            batch_df["dolocationid"].isin(valid_locations)
            ]

        # Append the DataFrame to the combined DataFrame
        combined_df = pd.concat([combined_df, batch_df], ignore_index=True)

    return combined_df


def write_combined_df(combined_df, output_dir):
    # Define the output file name
    output_file = os.path.join(output_dir, f"combined_{len(combined_df)}.pkl")

    # Write the combined DataFrame to the file
    combined_df.to_pickle(output_file)

    print(f"Combined DataFrame saved to: {output_file}")


if __name__ == "__main__":
    gdf = gpd.read_file("../NYC Taxi Zones.geojson")
    gdf = gdf[gdf['borough'] == 'Manhattan']
    manhattan_locations = gdf['location_id'].astype(int)

    combined_df = combine_batches(INPUT_DIR, manhattan_locations)
    write_combined_df(combined_df, OUTPUT_DIR)
