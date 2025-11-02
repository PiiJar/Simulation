"""
Main pipeline for production line simulation and optimization.
"""

import os
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_phase_1 import optimize_phase_1
from generate_matrix import generate_matrix
from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
from visualize_matrix import visualize_matrix
from simulation_logger import init_logger
from generate_production_report import generate_production_report

def main():
    from simulation_logger import get_logger
    
    print("🚀 Starting simulation pipeline...")

    # --- 1. Initialization ---
    print("📁 Creating simulation directory...")
    output_dir = create_simulation_directory()
    print(f"📂 Output directory: {output_dir}")
    logger = init_logger(output_dir)
    logger.log('STEP', 'Initialization started')
    generate_batch_treatment_programs(output_dir)
    logger.log('STEP', 'Initializtion ready')

    # --- 2. Preprocessing ---
    print("\n🔄 Preprocessing data for CP-SAT...")
    logger.log('STEP', 'Preprocessing started')
    preprocess_for_cpsat(output_dir)
    logger.log('STEP', 'Preprocessing ready')

    # --- 3. Optimization Phase 1: Station Optimization ---
    print("\n🧮 Starting CP-SAT Phase 1 optimization...")
    logger.log('STEP', 'CP-SAT Phase 1 optimization started')
    try:
        schedule_df = optimize_phase_1(output_dir)
        print(f"✅ Phase 1 optimization completed successfully")
        print(f"📊 Generated schedule with {len(schedule_df)} tasks")
        logger.log('STEP', 'CP-SAT Phase 1 optimization completed successfully')
    except Exception as e:
        error_msg = f'CP-SAT Phase 1 optimization failed: {str(e)}'
        print(f"❌ {error_msg}")
        logger.log('ERROR', error_msg)
        return

    # --- 4. Results ---
    # logger.log('STEP', 'Result collection started')
    # generate_matrix(output_dir)
    # extract_transporter_tasks(output_dir)
    #create_detailed_movements(output_dir)
    #logger.log('STEP', 'Resul collection ready')

    # Visualization and reporting
    # logger.log('STEP', 'Reporting started')
    # visualize_matrix(output_dir)
    # logger.log('STEP', 'Reportingready')
    # generate_production_report(output_dir)

    logger.log('STEP', 'Simulation and optimization pipeline completed')

if __name__ == "__main__":
    main()
