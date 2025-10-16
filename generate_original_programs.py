import os
import pandas as pd
import shutil

def generate_original_programs(output_dir, production_csv, treatment_programs_dir, original_programs_dir):
    os.makedirs(original_programs_dir, exist_ok=True)
    production = pd.read_csv(production_csv, dtype=str)
    for _, row in production.iterrows():
        batch = row['Batch'].zfill(3)
        program = row['Treatment_program'].zfill(3)
        src = os.path.join(treatment_programs_dir, f"Treatment_program_{program}.csv")
        dst = os.path.join(original_programs_dir, f"Batch_{batch}_Treatment_program_{program}.csv")
        shutil.copyfile(src, dst)
        print(f"Created original program: {dst}")

if __name__ == "__main__":
    generate_original_programs(
        output_dir=".",
        production_csv="initialization/Production.csv",
        treatment_programs_dir="initialization",
        original_programs_dir="original_programs"
    )
