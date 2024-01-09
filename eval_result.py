import os
import argparse
import re
import pandas as pd

def compute_metric(file_path):
    with open(file_path, "r") as txt_file:
        lines = txt_file.readlines()

    num_turns = 0
    num_yes = 0
    for line in lines:
        if "User:" in line:
            if "yes" in line.lower():
                num_yes += 1

    success = 1 if "bingo" in line.lower() else 0
    num_turns = int(re.search(r"Turn (\d+)", line).group(1))
    score = (1 - max(num_turns - 5, 0) * 0.02) if success == 1 else 0
    return num_turns, success, num_yes, score


def eval_q20(directory):
    data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                print(f"Computing {file_path}:")
                num_turns, success, num_yes, score = compute_metric(file_path)
                data.append({
                    'File': file[:-4],
                    'Num_Turns': num_turns,
                    'Success': success,
                    'Num_Yes': num_yes,
                    'Score': score
                })

    df = pd.DataFrame(data)
    avg_metrics = df.mean(numeric_only=True)
    avg_metrics['File'] = 'Average'

    # Print the average metrics
    print("Average Metrics:")
    print(avg_metrics.to_string(index=False))

    # Insert the average metrics as the first row
    df = pd.concat([pd.DataFrame([avg_metrics]), df], ignore_index=True)

    # Reorder columns to have "File" as the first column
    df = df[['File', 'Num_Turns', 'Success', 'Num_Yes', 'Score']]

    # Save DataFrame to a CSV file
    output_csv = os.path.join(args.dir, 'metrics.csv')
    df.round(decimals={'Num_Turns': 3, 'Success': 3, 'Num_Yes': 3, 'Score': 3}).to_csv(output_csv, index=False)
    print(f"Metrics saved to {output_csv}")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval Q20")
    parser.add_argument("--dir", type=str, help="Path to the directory containing TXT files.")
    args = parser.parse_args()

    eval_q20(args.dir)