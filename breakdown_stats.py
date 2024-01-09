import os
import pandas as pd
import argparse

# Define the input directory
parser = argparse.ArgumentParser(description="Breakdown Q20")
parser.add_argument("--dir", type=str, help="Path to the directory containing TXT files.")
parser.add_argument("--keep_order", action='store_true', help="Path to the directory containing TXT files.")
args = parser.parse_args()
input_dir = args.dir  # Replace with the actual input directory

# Get a list of subdirectories (fileX_repX) in the input directory
subdirectories = set([d[:-5] for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))])


# Create a dictionary to store data for each file name
file_data = {}

# Iterate through subdirectories
for subdir in subdirectories:
    # Create an empty DataFrame to store the cumulative data
    cumulative_data = pd.DataFrame(columns=["File", "Num_Turns", "Success", "Num_Yes", "Score"])
    skip_flag = False 

    # Iterate through the 5 repetitions
    for i in range(1, 6):
        # Define the file path for the metrics.csv file
        metrics_file = os.path.join(input_dir, f"{subdir}_rep{i}", "metrics.csv")
        
        if os.path.exists(metrics_file):
            # Read the metrics.csv file into a DataFrame
            data = pd.read_csv(metrics_file)
            
            # Add the data to the cumulative DataFrame
            cumulative_data = pd.concat([cumulative_data, data], ignore_index=True)

            if args.keep_order:
                # Store the unique file names in the order they appear
                file_order = data[data.keys()[0]].unique()

        else:
            print(f"Warning: missing {subdir}_rep{i}")
            skip_flag = True
            break
    
    if skip_flag:
        continue
    
    # Calculate the average for each column
    avg_data = cumulative_data.groupby("File").mean().reset_index()

    if args.keep_order:
        # Reorder rows in avg_data based on the original order of file names
        avg_data = avg_data.reindex(avg_data["File"].map({file: i for i, file in enumerate(file_order)}).sort_values().index)
    
    # Store the average data in the file_data dictionary
    file_data[subdir] = avg_data


# Write the average data to separate CSV files
for subdir, avg_data in file_data.items():
    output_file = os.path.join(input_dir, f"{subdir}.avg.csv")
    avg_data.to_csv(output_file, index=False)
