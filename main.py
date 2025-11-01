"""
Main pipeline for production line simulation and optimization.
"""

import os
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_optimization import cp_sat_optimization
from generate_matrix import generate_matrix
from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
from visualize_matrix import visualize_matrix
from simulation_logger import init_logger
from generate_production_report import generate_production_report

def main():
    from simulation_logger import get_logger

    # --- 1. Initialization ---
    output_dir = create_simulation_directory()
    logger = init_logger(output_dir)
    logger.log('STEP', 'Initialization started')
    generate_batch_treatment_programs(output_dir)
    logger.log('STEP', 'Initializtion ready')

    # --- 2. Preprocessing ---
    logger.log('STEP', 'Preprocessing started')
    preprocess_for_cpsat(output_dir)
    logger.log('STEP', 'Preprocessing ready')

    # --- 3. Optimization / Simulation ---
    logger.log('STEP', 'CP_SAT optimizatio started')
    model, task_vars, treatment_programs = cp_sat_optimization(output_dir, hard_order_constraint=True)
    # Check infeasibility solve_and_save:status
    from simulation_logger import get_last_optimization_status
    status = get_last_optimization_status(output_dir)
    if status == 'infeasible':
        logger.log('ERROR', 'Pipeline stopped: optimization infeasible, no further steps executed.')
        return
    # solve_and_save kutsutaan nyt cp_sat_optimization funktiossa
    logger.log('STEP', 'CP_SAT optimizatio  ready')

    # --- 4. Results ---
    logger.log('STEP', 'Result collection started')
    generate_matrix(output_dir)
    extract_transporter_tasks(output_dir)
    create_detailed_movements(output_dir)
    logger.log('STEP', 'Resul collection ready')

    # Visualization and reporting
    logger.log('STEP', 'Reporting started')
    visualize_matrix(output_dir)
    logger.log('STEP', 'Reportingready')
    # generate_production_report(output_dir)

    logger.log('STEP', 'Simulation and optimization pipeline completed')

if __name__ == "__main__":
    main()
