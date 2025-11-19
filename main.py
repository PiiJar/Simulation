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
    
    # Generate ALL batch treatment programs at initialization
    # (Phase 2 and Phase 3 will use only the batches in production.csv at that time)
    generate_batch_treatment_programs(output_dir)
    logger.log('INFO', 'Generated all batch treatment programs at initialization')
    
    # --- 1.5. Check if single program → create limited production for quick CP-SAT ---
    import pandas as pd
    production_csv = os.path.join(output_dir, 'initialization', 'production.csv')
    prod_df = pd.read_csv(production_csv)
    unique_programs = prod_df['Treatment_program'].nunique()
    
    use_quick_mode = (unique_programs == 1)
    
    if use_quick_mode:
        logger.log('INFO', f'Single program detected ({unique_programs}) → Quick mode enabled')
        
        # Calculate optimal Phase 2 batch count based on program duration and target cycle
        # Read treatment program to get total duration (processing + transport times)
        program_file = os.path.join(output_dir, 'initialization', 'treatment_program_001.csv')
        program_df = pd.read_csv(program_file)
        
        # Total program duration = sum of processing times + transport times
        # Convert MinTime (HH:MM:SS) to seconds
        program_df['MinTime_sec'] = pd.to_timedelta(program_df['MinTime']).dt.total_seconds()
        processing_time = program_df['MinTime_sec'].sum()
        
        # Transport time estimation: average transport between stations
        # Assuming ~30s average transport time per stage
        num_stages = len(program_df)
        transport_time = num_stages * 30  # seconds
        
        program_duration = processing_time + transport_time
        
        # Target cycle time: Use customer target or estimate from program
        # For now, use reasonable estimate: program_duration / 5
        target_cycle_time = max(600, program_duration / 5)  # Min 10 minutes
        
        # Calculate batches needed for pattern detection
        import math
        batches_on_line = math.ceil(program_duration / target_cycle_time)
        steady_cycles = 4  # Need 4 cycles to detect pattern reliably
        phase2_batches = batches_on_line + steady_cycles
        
        # Cap at reasonable maximum
        phase2_batches = min(phase2_batches, 20)
        
        logger.log('INFO', f'Program duration: {program_duration}s ({program_duration/60:.1f} min)')
        logger.log('INFO', f'Estimated target cycle: {target_cycle_time}s ({target_cycle_time/60:.1f} min)')
        logger.log('INFO', f'Batches on line when full: {batches_on_line}')
        logger.log('INFO', f'Phase 2 batches: {phase2_batches} (ramp-up: {batches_on_line}, steady: {steady_cycles})')
        
        # Varmuuskopioi alkuperäinen production.csv
        production_org = os.path.join(output_dir, 'initialization', 'production_org.csv')
        prod_df.to_csv(production_org, index=False)
        logger.log('INFO', f'Backup saved: production_org.csv ({len(prod_df)} batches)')
        
        # Phase 2: Luo rajoitettu production.csv
        quick_prod_df = prod_df.head(phase2_batches).copy()
        quick_prod_df.to_csv(production_csv, index=False)
        logger.log('INFO', f'Created limited production.csv for Phase 2: {len(quick_prod_df)} batches')
    else:
        logger.log('INFO', f'Multiple programs detected ({unique_programs}) → Normal mode')
    
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
    # Set time limit based on program count
    if use_quick_mode:
        phase2_time_limit = 300  # 5 minutes for single program
        logger.log('STEP', f'CP-SAT Phase 2 optimization started (Quick mode: {phase2_time_limit}s)')
    else:
        phase2_time_limit = None  # Use default from config
        logger.log('STEP', 'CP-SAT Phase 2 optimization started (Normal mode)')
    
    # Set environment variable for Phase 2 time limit
    original_time = os.environ.get("CPSAT_PHASE2_MAX_TIME")
    if phase2_time_limit is not None:
        os.environ["CPSAT_PHASE2_MAX_TIME"] = str(phase2_time_limit)
    
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
    finally:
        # Restore original time limit
        if original_time is not None:
            os.environ["CPSAT_PHASE2_MAX_TIME"] = original_time
        else:
            os.environ.pop("CPSAT_PHASE2_MAX_TIME", None)

    # --- 4.5. Pattern Mining (only if quick mode) ---
    if use_quick_mode:
        logger.log('STEP', 'Pattern mining started (searching for stage-based sequences)')
        try:
            from pattern_mining import find_cyclic_patterns, export_pattern_report
            
            # Find cyclic patterns in Phase 2 schedule
            patterns = find_cyclic_patterns(
                output_dir=output_dir,
                max_cycle_duration=7200,  # 2 hours max cycle
                require_complete=True      # Must include all stages
            )
            
            if patterns and len(patterns) > 0:
                best_pattern = patterns[0]
                logger.log('INFO', f'✓ Found {len(patterns)} complete cyclic pattern(s)')
                logger.log('INFO', f'✓ Best pattern: {best_pattern.duration}s duration, {best_pattern.throughput:.2f} batches/hour')
                logger.log('INFO', f'✓ Pattern covers {len(best_pattern.tasks_in_cycle)} tasks, {best_pattern.batches_completed} batches')
                
                # Export pattern reports (non-critical, ignore errors)
                try:
                    for i, p in enumerate(patterns[:3]):  # Top 3 patterns
                        export_pattern_report(p, output_dir, i)
                    logger.log('INFO', 'Pattern reports exported successfully')
                except Exception as export_err:
                    logger.log('WARNING', f'Pattern report export failed (non-critical): {export_err}')
                
                logger.log('STEP', 'Pattern mining completed - pattern detected')
            else:
                logger.log('INFO', 'No complete cyclic patterns found')
                logger.log('STEP', 'Pattern mining completed - no pattern found')
        except Exception as e:
            logger.log('WARNING', f'Pattern mining failed (non-critical): {str(e)}')
            import traceback
            traceback.print_exc()
            print(f"⚠ Pattern mining failed: {str(e)}")
        
        # --- 4.6. Restore full production for Phase 3 ---
        logger.log('STEP', 'Restoring full production for Phase 3')
        production_org = os.path.join(output_dir, 'initialization', 'production_org.csv')
        if os.path.exists(production_org):
            # Restore original production.csv
            prod_org_df = pd.read_csv(production_org)
            prod_org_df.to_csv(production_csv, index=False)
            logger.log('INFO', f'Restored production.csv: {len(prod_org_df)} batches')
            # Note: All treatment programs already created at initialization
        else:
            logger.log('WARNING', 'production_org.csv not found - skipping restoration')
        
        # --- 4.7. CP-SAT Phase 3: Extended optimization (with or without pattern) ---
        from cp_sat_phase_3 import optimize_phase_3
        
        logger.log('STEP', 'CP-SAT Phase 3 optimization started (seeking OPTIMAL)')
        try:
            ok = optimize_phase_3(output_dir)
            if not ok:
                error_msg = 'CP-SAT Phase 3 returned no solution (infeasible)'
                logger.log('ERROR', error_msg)
                return
            logger.log('STEP', 'CP-SAT Phase 3 optimization completed successfully')
        except Exception as e:
            error_msg = f'CP-SAT Phase 3 optimization failed: {str(e)}'
            logger.log('ERROR', error_msg)
            return
    else:
        logger.log('INFO', 'Pattern mining skipped (normal mode with multiple programs)')
        logger.log('INFO', 'Phase 3 skipped (only used in quick mode)')

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
        import traceback
        traceback.print_exc()
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
