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
from visualize_matrix import visualize_matrix
from simulation_logger import init_logger


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

    # --- 4. Optimization Phase 2: Hoist + Final schedule ---
    print("\n🧮 Starting CP-SAT Phase 2 optimization...")
    logger.log('STEP', 'CP-SAT Phase 2 optimization started')
    try:
        ok = optimize_phase_2(output_dir)
        if not ok:
            error_msg = 'CP-SAT Phase 2 returned no solution (infeasible)'
            print(f"❌ {error_msg}")
            logger.log('ERROR', error_msg)
            return
        print("✅ Phase 2 optimization completed successfully")
        logger.log('STEP', 'CP-SAT Phase 2 optimization completed successfully')
    except Exception as e:
        error_msg = f'CP-SAT Phase 2 optimization failed: {str(e)}'
        print(f"❌ {error_msg}")
        logger.log('ERROR', error_msg)
        return

    # --- 5. Results ---
    logger.log('STEP', 'Result collection started')
    try:
        generate_matrix(output_dir)
        extract_transporter_tasks(output_dir)
        create_detailed_movements(output_dir)
        logger.log('STEP', 'Result collection ready')
    except Exception as e:
        error_msg = f'Result collection failed: {str(e)}'
        print(f"❌ {error_msg}")
        logger.log('ERROR', error_msg)
        return

    # Visualization and reporting
    logger.log('STEP', 'Reporting started')

    from generate_simulation_report import generate_simulation_report
    try:
        visualize_matrix(output_dir)
        generate_simulation_report(output_dir)
        logger.log('STEP', 'Reporting ready')
    except Exception as e:
        error_msg = f'Reporting failed: {str(e)}'
        print(f"❌ {error_msg}")
        logger.log('ERROR', error_msg)
        return

    logger.log('STEP', 'Simulation and optimization pipeline completed')

if __name__ == "__main__":
    main()
