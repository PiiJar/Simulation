#!/usr/bin/env python3
"""
Test ONLY the stretch function
"""
import os
import shutil
from simulation_logger import init_logger
from stretch_transporter_tasks import stretch_tasks

def test_stretch_only():
    # Käytä olemassa olevaa output-kansiota
    output_dirs = [d for d in os.listdir("output") if d.startswith("2025-08-08")]
    if not output_dirs:
        print("No output directories found")
        return
    
    # Käytä uusinta kansiota
    latest_dir = sorted(output_dirs)[-1]
    output_dir = os.path.join("output", latest_dir)
    
    print(f"Using output directory: {output_dir}")
    
    # Luo backup
    backup_dir = output_dir + "_backup"
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    shutil.copytree(output_dir, backup_dir)
    print(f"Created backup: {backup_dir}")
    
    # Alusta logger
    init_logger(output_dir)
    
    # Aja vain stretch
    print("Running stretch_tasks...")
    stretch_tasks(output_dir)
    print("Stretch completed!")
    
    # Tarkista muutokset
    prog_file = os.path.join(output_dir, "optimized_programs", "batch_001_treatment_program_001.csv")
    if os.path.exists(prog_file):
        with open(prog_file, 'r') as f:
            lines = f.readlines()
        print(f"Stage 3 line: {lines[3].strip()}")  # Stage 3 on 4. rivi (0-indexed 3)
    
if __name__ == "__main__":
    test_stretch_only()
