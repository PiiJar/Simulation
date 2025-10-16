import os
import pandas as pd

def create_sorted_line_matrix(output_dir):
    logs_dir = os.path.join(output_dir, "logs")
    input_file = os.path.join(logs_dir, "line_matrix_stretched.csv")
    output_file = os.path.join(logs_dir, "line_matrix_stretched_sorted.csv")
    df = pd.read_csv(input_file)
    df_sorted = df.sort_values(["EntryTime", "Batch", "Stage"]).reset_index(drop=True)
    df_sorted.to_csv(output_file, index=False)
    return output_file

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    create_sorted_line_matrix(output_dir)
