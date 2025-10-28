"""
Main pipeline for production line simulation and optimization.
"""

import os
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_stepwise import cp_sat_stepwise, solve_and_save
from generate_matrix_stretched import generate_matrix_stretched
from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
from visualize_stretched_matrix import visualize_stretched_matrix
from simulation_logger import init_logger
from generate_production_report import generate_production_report

def main():
    # --- 1. Initialization ---
    # Create simulation directory and copy all input data
    output_dir = create_simulation_directory()
    generate_batch_treatment_programs(output_dir)

    # --- 2. Preprocessing ---
    # Transform and validate input data for optimization
    # preprocess_for_cpsat(output_dir)

    # --- 3. Optimization / Simulation ---
    # Solve production scheduling with CP-SAT model (hard order constraint)
    # model, task_vars, treatment_programs = cp_sat_stepwise(output_dir, hard_order_constraint=True)
    # solve_and_save(model, task_vars, treatment_programs, output_dir)

    # --- 4. Results ---
    # Generate stretched matrix and transporter movements
    # generate_matrix_stretched(output_dir)
    # extract_transporter_tasks(output_dir)
    # create_detailed_movements(output_dir)

    # Visualization and reporting
    # init_logger(output_dir)
    # visualize_stretched_matrix(output_dir)
    #generate_production_report(output_dir)

    print("[PIPELINE] Simulation and optimization pipeline completed.")

if __name__ == "__main__":
    main()
