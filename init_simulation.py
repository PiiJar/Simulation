"""
Initialize simulation without running the full pipeline.
Creates output directory, goals, production data, and batch treatment programs.
"""

import os
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs import generate_batch_treatment_programs
from simulation_logger import init_logger
from generate_goals import generate_goals


def init_simulation():
    """Run only the initialization phase of the simulation."""
    from simulation_logger import get_logger

    # --- 1. Initialization ---
    output_dir = create_simulation_directory()
    logger = init_logger(output_dir)
    logger.log('STEP', 'Initialization started')

    # Create goals.json and production.csv FIRST
    try:
        generate_goals(output_dir)
        logger.log('STEP', 'Goals and production.csv generated')
    except Exception as e:
        error_msg = f'Goals generation failed: {str(e)}'
        logger.log('ERROR', error_msg)
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return None

    # Then create batch treatment programs based on production.csv
    try:
        generate_batch_treatment_programs(output_dir)
        logger.log('STEP', 'Initialization ready')
        print(f"✅ Initialization completed successfully")
        print(f"📁 Output directory: {output_dir}")
        return output_dir
    except Exception as e:
        error_msg = f'Batch treatment programs generation failed: {str(e)}'
        logger.log('ERROR', error_msg)
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    init_simulation()