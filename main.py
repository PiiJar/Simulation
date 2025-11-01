"""
Main pipeline for production line simulation and optimization.
"""

import os
import pandas as pd
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_optimization_REAL import cp_sat_optimization_REAL
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
    
    # Lue tarvittavat tiedot cp_sat kansiosta
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    
    batches_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_batches.csv"))
    stations_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"))
    transfers_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv"))
    transporters_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"))
    
    # Lue käsittelyohjelmat
    treatment_programs = {}
    for _, batch_row in batches_df.iterrows():
        batch_id = batch_row['Batch']  # Oikea sarakkeen nimi
        program_file = os.path.join(cp_sat_dir, f"cp_sat_treatment_program_{batch_id}.csv")
        treatment_programs[batch_id] = pd.read_csv(program_file)
    
    success = cp_sat_optimization_REAL(
        output_dir=output_dir,
        treatment_programs=treatment_programs,
        batches_df=batches_df,
        stations_df=stations_df,
        transfers_df=transfers_df,
        transporters_df=transporters_df,
        hard_order_constraint=False
    )
    
    if not success:
        logger.log('ERROR', 'Pipeline stopped: optimization failed')
        return
        
    logger.log('STEP', 'CP_SAT optimizatio ready')

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
