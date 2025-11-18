"""
Main pipeline for production line simulation and optimization.
"""

import os
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_phase_1 import optimize_phase_1
from cp_sat_phase_2 import optimize_phase_2
from generate_matrix import generate_matrix
from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
from repair_report_data import repair_report_data
from visualize_matrix import visualize_matrix
from simulation_logger import init_logger
from generate_goals import generate_goals


def main():
    from simulation_logger import get_logger
    
    # --- 1. Initialization ---
    output_dir = create_simulation_directory()
    logger = init_logger(output_dir)
    logger.log('STEP', 'Initialization started')
    # Luo goals.json ja production.csv ENSIN
    try:
        generate_goals(output_dir)
        logger.log('STEP', 'Goals and production.csv generated')
    except Exception as e:
        error_msg = f'Goals generation failed: {str(e)}'
        logger.log('ERROR', error_msg)
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return
    # Sitten luo batch treatment programs production.csv:n pohjalta
    generate_batch_treatment_programs(output_dir)
    logger.log('STEP', 'Initializtion ready')

    # --- 2. Preprocessing ---
    logger.log('STEP', 'Preprocessing started')
    preprocess_for_cpsat(output_dir)
    logger.log('STEP', 'Preprocessing ready')

    # --- 3. Optimization Phase 1: Station Optimization ---
    logger.log('STEP', 'CP-SAT Phase 1 optimization started')
    try:
        schedule_df = optimize_phase_1(output_dir)
        logger.log('STEP', 'CP-SAT Phase 1 optimization completed successfully')
    except Exception as e:
        error_msg = f'CP-SAT Phase 1 optimization failed: {str(e)}'
        logger.log('ERROR', error_msg)
        return

    # --- 4. Optimization Phase 2: Transporter + Final schedule ---
    logger.log('STEP', 'CP-SAT Phase 2 optimization started')
    try:
        ok = optimize_phase_2(output_dir)
        if not ok:
            error_msg = 'CP-SAT Phase 2 returned no solution (infeasible)'
            logger.log('ERROR', error_msg)
            return
        logger.log('STEP', 'CP-SAT Phase 2 optimization completed successfully')
    except Exception as e:
        error_msg = f'CP-SAT Phase 2 optimization failed: {str(e)}'
        logger.log('ERROR', error_msg)
        return

    # --- 5. Results ---
    logger.log('STEP', 'Result collection started')
    try:
        generate_matrix(output_dir)
        extract_transporter_tasks(output_dir)
        create_detailed_movements(output_dir)
        repair_report_data(output_dir)
        logger.log('STEP', 'Result collection ready')
    except Exception as e:
        error_msg = f'Result collection failed: {str(e)}'
        logger.log('ERROR', error_msg)
        return

    # Visualization and reporting
    logger.log('STEP', 'Reporting started')

    from collect_report_data import collect_report_data
    from generate_simulation_report import generate_simulation_report
    from generate_images import generate_images
    try:
        visualize_matrix(output_dir)
        collect_report_data(output_dir)  # Collect data to report_data.json
        generate_images(output_dir)  # Generate all report images (cards, charts, etc.)
        generate_simulation_report(output_dir)  # Simulation report
        logger.log('STEP', 'Reporting ready')
    except Exception as e:
        error_msg = f'Reporting failed: {str(e)}'
        print(f"❌ {error_msg}")
        logger.log('ERROR', error_msg)
        return

    logger.log('STEP', 'Simulation and optimization pipeline completed')

if __name__ == "__main__":
    main()
