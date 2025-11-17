"""
Collect all simulation data into a single JSON file for reporting.

This module gathers simulation metadata, statistics, and file paths
into a centralized report_data.json file that can be used by report generators.
"""

import os
import json
from datetime import datetime
from load_customer_json import load_customer_json
import pandas as pd


def collect_report_data(output_dir: str):
    """
    Collect simulation data and save to report_data.json in reports directory.
    
    Args:
        output_dir: Path to simulation output directory
    
    Creates:
        reports/report_data.json with simulation metadata and references
    """
    init_dir = os.path.join(output_dir, 'initialization')
    reports_dir = os.path.join(output_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Initialize report data structure
    report_data = {
        "simulation_info": {},
        "simulation": {},  # Quick access metrics for cards
        "files": {},
        "batch_statistics": [],
        "transporter_statistics": [],
        "station_utilization": [],
        "treatment_programs": {
            "used_programs": [],
            "programs": {}
        }
    }

    # Load station metadata early for use when summarizing treatment programs
    station_group_map = {}
    station_numbers_sorted = []
    stations_json_path = os.path.join(init_dir, 'stations.json')
    if os.path.exists(stations_json_path):
        try:
            with open(stations_json_path, 'r', encoding='utf-8') as f:
                stations_payload = json.load(f)
            station_entries = stations_payload.get('stations', [])
            for entry in station_entries:
                station_number = entry.get('number')
                station_group = entry.get('group', station_number)
                if station_number is None:
                    continue
                try:
                    number = int(station_number)
                except (TypeError, ValueError):
                    continue
                try:
                    group = int(station_group) if station_group is not None else number
                except (TypeError, ValueError):
                    group = number
                station_group_map[number] = group
            station_numbers_sorted = sorted(station_group_map.keys())
        except Exception as e:
            print(f"⚠️  Warning: Could not load stations metadata: {e}")
    else:
        print(f"⚠️  Warning: stations.json not found at {stations_json_path}")

    def parse_time_to_seconds(time_str):
        """Convert HH:MM:SS time string to seconds."""
        if pd.isna(time_str):
            return 0
        try:
            parts = str(time_str).split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(float, parts)
                return hours * 3600 + minutes * 60 + seconds
        except Exception:
            pass
        return 0

    def calculate_stage_transfer_times(stage: int, min_station: int, max_station: int, df_transfer):
        """
        Calculate average transfer times for a specific stage.
        
        Args:
            stage: Stage number
            min_station: Minimum station number for this stage
            max_station: Maximum station number for this stage
            df_transfer: DataFrame with transfer task data
            
        Returns:
            dict with 'transfer_in', 'transfer_out', 'total_in', 'total_out', 'sum_total'
        """
        # Find the previous stage's station (where batches come from)
        # Look for transfers TO current stage stations
        transfers_to_stage = df_transfer[
            df_transfer['To_Station'].between(min_station, max_station)
        ]
        
        if len(transfers_to_stage) > 0:
            # Get unique from_stations (where batches come from)
            from_stations = transfers_to_stage['From_Station'].unique()
            
            # Transfers IN: from previous stage to current stage
            transfers_in = df_transfer[
                (df_transfer['From_Station'].isin(from_stations)) &
                (df_transfer['To_Station'].between(min_station, max_station))
            ]
            
            avg_transfer_in = transfers_in['TransferTime'].mean() if len(transfers_in) > 0 else 0
            avg_total_in = transfers_in['TotalTaskTime'].mean() if len(transfers_in) > 0 else 0
        else:
            avg_transfer_in = 0
            avg_total_in = 0
        
        # Find the next stage's station (where batches go to)
        transfers_from_stage = df_transfer[
            df_transfer['From_Station'].between(min_station, max_station)
        ]
        
        if len(transfers_from_stage) > 0:
            # Get unique to_stations (where batches go to)
            to_stations = transfers_from_stage['To_Station'].unique()
            
            # Transfers OUT: from current stage to next stage
            transfers_out = df_transfer[
                (df_transfer['From_Station'].between(min_station, max_station)) &
                (df_transfer['To_Station'].isin(to_stations))
            ]
            
            avg_transfer_out = transfers_out['TransferTime'].mean() if len(transfers_out) > 0 else 0
            avg_total_out = transfers_out['TotalTaskTime'].mean() if len(transfers_out) > 0 else 0
        else:
            avg_transfer_out = 0
            avg_total_out = 0
        
        return {
            'transfer_in': avg_transfer_in,
            'transfer_out': avg_transfer_out,
            'total_in': avg_total_in,
            'total_out': avg_total_out,
            'sum_total': avg_total_in + avg_total_out
        }

    def summarize_treatment_program(program_number: int, avg_transfer_time: float = 0, avg_total_task_time: float = 0, df_transfer = None):
        candidates = [
            os.path.join(init_dir, f'treatment_program_{program_number:03d}.csv')
        ]
        df_tp = None
        source_path = None
        for candidate in candidates:
            if os.path.exists(candidate):
                try:
                    df_tp = pd.read_csv(candidate)
                    source_path = candidate
                    break
                except Exception as e:
                    print(f"⚠️  Warning: Could not read treatment program file {candidate}: {e}")
                    return None
        if df_tp is None or df_tp.empty:
            print(f"⚠️  Warning: Treatment program {program_number} definition is missing or empty")
            return None

        steps = []
        for _, row in df_tp.iterrows():
            stage_val = row.get('Stage')
            min_stat_val = row.get('MinStat')
            max_stat_val = row.get('MaxStat')
            min_time_val = row.get('MinTime')
            max_time_val = row.get('MaxTime')

            stage = int(stage_val) if pd.notna(stage_val) else None
            min_station = int(pd.to_numeric(min_stat_val, errors='coerce')) if pd.notna(min_stat_val) else None
            max_station = int(pd.to_numeric(max_stat_val, errors='coerce')) if pd.notna(max_stat_val) else None
            minimum_treatment_time = parse_time_to_seconds(min_time_val)
            maximum_treatment_time = parse_time_to_seconds(max_time_val)

            lower = min_station
            upper = max_station
            if min_station is not None and max_station is not None and min_station > max_station:
                lower, upper = max_station, min_station

            group_counts = {}
            if lower is not None and upper is not None and station_numbers_sorted:
                for station_number in station_numbers_sorted:
                    if station_number < lower:
                        continue
                    if station_number > upper:
                        break
                    group_number = station_group_map.get(station_number)
                    if group_number is None:
                        continue
                    group_counts.setdefault(group_number, []).append(station_number)

            min_group = station_group_map.get(min_station) if min_station is not None else None
            max_group = station_group_map.get(max_station) if max_station is not None else None

            parallel_groups = [
                {
                    'group': group_key,
                    'station_numbers': sorted(numbers),
                    'count': len(numbers)
                }
                for group_key, numbers in sorted(group_counts.items())
            ]

            min_group_parallel_count = len(group_counts.get(min_group, [])) if min_group is not None else 0
            
            # Calculate stage-specific transfer times if df_transfer is available
            if df_transfer is not None:
                stage_transfers = calculate_stage_transfer_times(stage, min_station, max_station, df_transfer)
                stage_total_task = stage_transfers['sum_total']
            else:
                # Fallback to global average
                stage_total_task = 2 * avg_total_task_time
            
            # Calculate minimum_cycle_time (bottleneck analysis)
            # Formula: (minimum_treatment_time + stage_specific_transfer_times) / min_group_parallel_count
            if min_group_parallel_count > 0:
                minimum_cycle_time = (minimum_treatment_time + stage_total_task) / min_group_parallel_count
            else:
                minimum_cycle_time = 0

            steps.append({
                'stage': stage,
                'min_station': min_station,
                'max_station': max_station,
                'min_station_group': min_group,
                'parallel_groups': parallel_groups,
                'min_group_parallel_count': min_group_parallel_count,
                'minimum_treatment_time_seconds': round(minimum_treatment_time, 2),
                'maximum_treatment_time_seconds': round(maximum_treatment_time, 2),
                'minimum_cycle_time_seconds': round(minimum_cycle_time, 2)
            })

        # Calculate total throughput times for the entire program
        num_steps = len(steps)
        total_transfer_time = num_steps * avg_total_task_time
        
        # Minimum total throughput = sum of minimum cycle times + total transfer time
        total_minimum_cycle_time = sum(step['minimum_cycle_time_seconds'] for step in steps)
        total_minimum_throughput = total_minimum_cycle_time + total_transfer_time
        
        # Maximum total throughput = sum of maximum treatment times + total transfer time
        total_maximum_treatment_time = sum(step['maximum_treatment_time_seconds'] for step in steps)
        total_maximum_throughput = total_maximum_treatment_time + total_transfer_time

        return {
            'program_number': program_number,
            'source_file': os.path.relpath(source_path, output_dir) if source_path else None,
            'steps': steps,
            'total_minimum_throughput_seconds': round(total_minimum_throughput, 2),
            'total_maximum_throughput_seconds': round(total_maximum_throughput, 2),
            'throughput_calculation': {
                'num_steps': num_steps,
                'avg_task_time_per_step': round(avg_total_task_time, 2),
                'total_transfer_time': round(total_transfer_time, 2),
                'total_minimum_cycle_time': round(total_minimum_cycle_time, 2),
                'total_maximum_treatment_time': round(total_maximum_treatment_time, 2),
                'formula_minimum': f'sum(minimum_cycle_times) + (num_steps × avg_task_time) = {total_minimum_cycle_time:.2f} + {total_transfer_time:.2f} = {total_minimum_throughput:.2f}s',
                'formula_maximum': f'sum(maximum_treatment_times) + (num_steps × avg_task_time) = {total_maximum_treatment_time:.2f} + {total_transfer_time:.2f} = {total_maximum_throughput:.2f}s'
            }
        }
    
    # --- Simulation Info ---
    # Load customer and plant data
    products_dict = {}  # Dictionary to store product info by ID
    production_schedule = {}  # Store production schedule info
    product_targets = {}  # Dictionary to store target quantities by product ID
    total_target_quantity = 0  # Total of all target quantities for ratio calculation
    
    try:
        customer, plant, products = load_customer_json(init_dir)
        report_data["simulation_info"]["customer_id"] = customer.get("id", "")
        report_data["simulation_info"]["customer_name"] = customer.get("name", "")
        report_data["simulation_info"]["plant_id"] = plant.get("id", "")
        report_data["simulation_info"]["plant_name"] = plant.get("name", "")
        report_data["simulation_info"]["plant_location"] = plant.get("location", "")
        report_data["simulation_info"]["available_containers"] = plant.get("available_containers", 50)
        
        # Get production schedule (shifts per day, hours per shift, etc.)
        production_schedule = plant.get("production_schedule", {})
        shifts_per_day = production_schedule.get("shifts_per_day", 2)
        hours_per_shift = production_schedule.get("hours_per_shift", 8.0)
        days_per_week = production_schedule.get("days_per_week", 5)
        
        # Get production targets for product distribution
        production_targets_list = plant.get("production_targets", {}).get("annual", [])
        for target in production_targets_list:
            product_id = target.get("product_id", "")
            target_qty = target.get("target_quantity", 0)
            if product_id and target_qty > 0:
                product_targets[product_id] = target_qty
                total_target_quantity += target_qty
        
        # Store product information for later use
        for product in products:
            product_id = product.get("id", "")
            properties = product.get("properties", {})
            products_dict[product_id] = {
                "name": product.get("name", ""),
                "description": product.get("description", ""),
                "pieces_per_batch": properties.get("pieces_per_batch", 1)
            }
    except Exception as e:
        print(f"Warning: Could not load customer.json: {e}")
        report_data["simulation_info"]["customer_id"] = ""
        report_data["simulation_info"]["customer_name"] = "[Customer data not available]"
        report_data["simulation_info"]["plant_id"] = ""
        report_data["simulation_info"]["plant_name"] = "[Plant data not available]"
        report_data["simulation_info"]["plant_location"] = ""
        shifts_per_day = 2
        hours_per_shift = 8.0
        days_per_week = 5
        product_targets = {}
        total_target_quantity = 0
    
    # Simulation directory name
    folder_name = os.path.basename(os.path.abspath(output_dir))
    report_data["simulation_info"]["folder_name"] = folder_name
    
    # Timestamp
    now = datetime.now()
    report_data["simulation_info"]["report_generated"] = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # Load goals.json for simulation duration (from initialization directory)
    goals_path = os.path.join(init_dir, 'goals.json')
    target_cycle_time_seconds = None
    if os.path.exists(goals_path):
        try:
            with open(goals_path, 'r') as f:
                goals = json.load(f)
                report_data["simulation_info"]["simulation_duration_hours"] = goals.get("simulation_duration_hours", 0.0)
                # Extract target cycle time from goals
                target_pace = goals.get("target_pace", {})
                # Use the new annual target cycle time if available, otherwise fall back to average_batch_interval_seconds
                target_cycle_time_seconds = target_pace.get("target_cycle_time_seconds") or target_pace.get("average_batch_interval_seconds")
        except Exception as e:
            print(f"Warning: Could not load goals.json: {e}")
            report_data["simulation_info"]["simulation_duration_hours"] = 0.0
    else:
        report_data["simulation_info"]["simulation_duration_hours"] = 0.0
    
    # --- Production Phase Times ---
    # Calculate ramp-up, steady-state, and ramp-down times
    try:
        import pandas as pd
        
        # Read production.csv to count batches and products
        production_path = os.path.join(init_dir, 'production.csv')
        total_batches = 0
        product_counts = {}

        # Load transfer task statistics first (needed for cycle time calculations)
        avg_transfer_time = 0
        avg_total_task_time = 0
        try:
            transfer_tasks_path = os.path.join(output_dir, 'cp_sat', 'cp_sat_transfer_tasks.csv')
            if os.path.exists(transfer_tasks_path):
                df_transfer = pd.read_csv(transfer_tasks_path)
                if 'TransferTime' in df_transfer.columns and 'TotalTaskTime' in df_transfer.columns:
                    avg_transfer_time = df_transfer['TransferTime'].mean()
                    avg_total_task_time = df_transfer['TotalTaskTime'].mean()
                    report_data["transfer_task_statistics"] = {
                        "avg_transfer_time_seconds": round(avg_transfer_time, 2),
                        "avg_total_task_time_seconds": round(avg_total_task_time, 2),
                        "total_transfer_tasks": len(df_transfer)
                    }
                    print(f"✅ Transfer task statistics: avg_transfer={avg_transfer_time:.2f}s, avg_total={avg_total_task_time:.2f}s")
        except Exception as e:
            print(f"⚠️  Warning: Could not calculate transfer task statistics: {e}")

        if os.path.exists(production_path):
            df_production = pd.read_csv(production_path)
            total_batches = len(df_production)

            # Capture the distinct treatment programs encountered in production.csv
            if 'Treatment_program' in df_production.columns:
                treatment_program_set = sorted(df_production['Treatment_program'].dropna().astype(int).unique())
                report_data['treatment_programs']['used_programs'] = [int(hp) for hp in treatment_program_set]
                for treatment_program in treatment_program_set:
                    summary = summarize_treatment_program(int(treatment_program), avg_transfer_time, avg_total_task_time, df_transfer)
                    if summary is not None:
                        report_data['treatment_programs']['programs'][int(treatment_program)] = summary

            # Count by Treatment_program (which corresponds to product)
            # Map treatment program to product ID from customer.json
            if 'Treatment_program' in df_production.columns:
                for idx, row in df_production.iterrows():
                    treatment_program = row['Treatment_program']

                    # Find matching product by treatment_program
                    product_id = None
                    product_name = f"Treatment Program {treatment_program}"

                    for pid, pinfo in products_dict.items():
                        # Check if this product uses this treatment program
                        # For now, use treatment program number as identifier
                        # In the future, this mapping should come from customer.json
                        if treatment_program == 1:  # Assuming treatment program 1 = PROD-001
                            product_id = pid
                            product_name = pinfo.get("name", f"Product {pid}")
                            break

                    # Count this product
                    if product_id:
                        if product_id not in product_counts:
                            product_counts[product_id] = {"name": product_name, "count": 0}
                        product_counts[product_id]["count"] += 1
                    else:
                        # Fallback to treatment program as key
                        key = f"TreatmentProgram_{treatment_program}"
                        if key not in product_counts:
                            product_counts[key] = {"name": product_name, "count": 0}
                        product_counts[key]["count"] += 1
        
        report_data["simulation_info"]["total_batches"] = total_batches
        
        # Read batch schedule to find batch timings
        batch_schedule_path = os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv')
        
        if os.path.exists(batch_schedule_path):
            df_schedule = pd.read_csv(batch_schedule_path)
            
            if not df_schedule.empty:
                
                # Helper function for time formatting
                def seconds_to_hms(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    s = int(seconds % 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"
                
                # Find first batch's completion time (ramp-up end)
                # Steady state starts when first batch completes
                first_batch_num = df_schedule['Batch'].min()
                first_batch = df_schedule[df_schedule['Batch'] == first_batch_num]
                ramp_up_end = first_batch['ExitTime'].max()
                
                # Find when last batch started (ramp-down start)
                # Steady state ends when last batch starts (enters first stage)
                last_batch_num = df_schedule['Batch'].max()
                last_batch = df_schedule[df_schedule['Batch'] == last_batch_num]
                ramp_down_start = last_batch['EntryTime'].min()
                
                # Find when the last finishing batch ends (ramp-down end)
                # Maximum ExitTime across all batches
                ramp_down_end = df_schedule['ExitTime'].max()
                
                # Calculate phase durations
                report_data["simulation_info"]["ramp_up_time_seconds"] = int(ramp_up_end)
                report_data["simulation_info"]["steady_state_time_seconds"] = int(ramp_down_start - ramp_up_end)
                report_data["simulation_info"]["ramp_down_time_seconds"] = int(ramp_down_end - ramp_down_start)
                
                # Check if steady state actually exists
                if ramp_down_start <= ramp_up_end:
                    print(f"⚠️  Warning: Ramp-up and ramp-down overlap - no steady state production phase.")
                    print(f"   This is normal with few batches. Increase batch count for steady state.")
                    print(f"   Ramp-up ends: {seconds_to_hms(ramp_up_end)}, Ramp-down starts: {seconds_to_hms(ramp_down_start)}")
                    report_data["simulation_info"]["has_steady_state"] = False
                else:
                    report_data["simulation_info"]["has_steady_state"] = True
                
                # Store as formatted time strings (HH:MM:SS)
                report_data["simulation_info"]["ramp_up_time"] = seconds_to_hms(ramp_up_end)
                report_data["simulation_info"]["steady_state_time"] = seconds_to_hms(ramp_down_start - ramp_up_end)
                report_data["simulation_info"]["ramp_down_time"] = seconds_to_hms(ramp_down_end - ramp_down_start)
                report_data["simulation_info"]["total_production_time"] = seconds_to_hms(ramp_down_end)
                
                # Populate quick access simulation metrics for cards
                report_data["simulation"]["duration_seconds"] = int(ramp_down_end)
                report_data["simulation"]["total_batches"] = total_batches
                
                # Calculate steady-state average cycle time from actual batch completions
                try:
                    # Use production.csv for accurate batch start times
                    production_path = os.path.join(output_dir, 'initialization', 'production.csv')
                    if os.path.exists(production_path):
                        df_production = pd.read_csv(production_path)
                        
                        # Convert Start_optimized to seconds
                        df_production['Start_seconds'] = pd.to_timedelta(df_production['Start_optimized']).dt.total_seconds()
                        
                        # Find batches that START during steady-state
                        # Steady state: from first batch completion (ramp_up_end) to when last batch starts (ramp_down_start)
                        steady_batches = df_production[(df_production['Start_seconds'] >= ramp_up_end) & 
                                                       (df_production['Start_seconds'] < ramp_down_start)]
                        
                        if len(steady_batches) > 1:
                            first_batch_time = steady_batches['Start_seconds'].iloc[0]
                            last_batch_time = steady_batches['Start_seconds'].iloc[-1]
                            time_diff = last_batch_time - first_batch_time
                            avg_cycle_time = time_diff / (len(steady_batches) - 1)
                            
                            report_data["simulation"]["steady_state_avg_cycle_time_seconds"] = round(avg_cycle_time, 2)
                except Exception as e:
                    print(f"⚠️  Warning: Could not calculate steady-state cycle time: {e}")
                
                # --- Production Throughput Calculations ---
                # Calculate scaled production estimates for different time periods
                # Total production = steady_state + ramp_down completions
                if total_batches > 0 and ramp_down_end > 0:
                    
                    # For throughput calculations, use steady-state period if it exists
                    if report_data["simulation_info"]["has_steady_state"]:
                        # Steady-state window duration (for info only)
                        steady_state_duration = ramp_down_start - ramp_up_end
                        
                        # Use production.csv for batch start times
                        production_path = os.path.join(output_dir, 'initialization', 'production.csv')
                        if os.path.exists(production_path):
                            df_production = pd.read_csv(production_path)
                            df_production['Start_seconds'] = pd.to_timedelta(df_production['Start_optimized']).dt.total_seconds()
                            
                            # Find batches that START during steady state
                            steady_starts = df_production[(df_production['Start_seconds'] >= ramp_up_end) & 
                                                         (df_production['Start_seconds'] < ramp_down_start)]
                        
                        # Count batches completed during ramp-down (work in progress completion)
                        batches_completed_in_rampdown = 0
                        for batch in df_schedule['Batch'].unique():
                            batch_data = df_schedule[df_schedule['Batch'] == batch]
                            last_stage = batch_data['Stage'].max()
                            last_stage_data = batch_data[batch_data['Stage'] == last_stage]
                            
                            if not last_stage_data.empty:
                                exit_time = last_stage_data.iloc[0]['ExitTime']
                                if exit_time > ramp_down_start:
                                    batches_completed_in_rampdown += 1
                        
                        if len(steady_starts) > 1:
                            # Calculate throughput from actual start times from production.csv
                            first_start = steady_starts['Start_seconds'].iloc[0]
                            last_start = steady_starts['Start_seconds'].iloc[-1]
                            actual_steady_duration = last_start - first_start
                            
                            # Batches per second = intervals / duration
                            batches_per_second = (len(steady_starts) - 1) / actual_steady_duration
                            calculation_method = "steady_state_with_rampdown"
                            
                            report_data["simulation_info"]["steady_state_batches_started"] = len(steady_starts)
                            report_data["simulation_info"]["ramp_down_batches_completed"] = batches_completed_in_rampdown
                            report_data["simulation_info"]["ramp_up_time_seconds"] = int(ramp_up_end)
                            report_data["simulation_info"]["ramp_down_time_seconds"] = int(ramp_down_end - ramp_down_start)
                        else:
                            # Fallback to total if steady state calculation fails
                            batches_per_second = total_batches / ramp_down_end
                            calculation_method = "total_simulation"
                            batches_completed_in_rampdown = 0
                    else:
                        # No steady state exists (too few batches), use total simulation time
                        # This is less accurate for long-term projections
                        batches_per_second = total_batches / ramp_down_end
                        calculation_method = "total_simulation_no_steady_state"
                    
                    # Time periods in seconds
                    HOUR = 3600
                    DAY = 24 * HOUR
                    WEEK = 7 * DAY
                    MONTH = 30 * DAY  # Approximate 30 days
                    YEAR = 365 * DAY
                    
                    # Work shift duration
                    shift_duration_hours = hours_per_shift
                    shift_duration_seconds = shift_duration_hours * HOUR
                    
                    # Production weeks per year from customer data
                    production_weeks_per_year = production_schedule.get("weeks_per_year", 48)
                    
                    # Ramp times (in seconds)
                    ramp_up_seconds = report_data["simulation_info"]["ramp_up_time_seconds"]
                    ramp_down_seconds = report_data["simulation_info"]["ramp_down_time_seconds"]
                    
                    # Calculate ONE SHIFT production
                    steady_phase_shift = shift_duration_seconds - ramp_up_seconds - ramp_down_seconds
                    if steady_phase_shift > 0:
                        shift_batches = int(batches_per_second * steady_phase_shift + batches_completed_in_rampdown)
                    else:
                        shift_batches = batches_completed_in_rampdown
                    
                    # Calculate ONE DAY production
                    # Shifts run consecutively within the day (one ramp-up at start, one ramp-down at end)
                    total_shift_time_per_day = shifts_per_day * shift_duration_seconds
                    # Cap at 24 hours maximum
                    effective_production_time = min(total_shift_time_per_day, 24 * HOUR)
                    steady_phase_day = effective_production_time - ramp_up_seconds - ramp_down_seconds
                    
                    if steady_phase_day > 0:
                        day_batches = int(batches_per_second * steady_phase_day + batches_completed_in_rampdown)
                    else:
                        day_batches = batches_completed_in_rampdown
                    
                    # Check if this is continuous 24h production (affects week/month/year calculations)
                    is_continuous_24h = (total_shift_time_per_day >= 24 * HOUR)
                    
                    if is_continuous_24h:
                        day_note = f"Continuous 24h production ({shifts_per_day} shifts), one ramp-up at start, one ramp-down at end"
                    else:
                        day_note = f"{shifts_per_day} consecutive shifts, one ramp-up at start, one ramp-down at end"
                    
                    # WEEK, MONTH, YEAR calculations
                    if is_continuous_24h:
                        # Continuous production across multiple days - treat as one long production run
                        # Week: days_per_week × 24h - one ramp_up - one ramp_down
                        steady_phase_week = (days_per_week * 24 * HOUR) - ramp_up_seconds - ramp_down_seconds
                        week_batches = int(batches_per_second * steady_phase_week + batches_completed_in_rampdown)
                        week_note = f"Continuous {days_per_week}-day production, one ramp-up at start, one ramp-down at end"
                        
                        # Month: 22 workdays × 24h - one ramp_up - one ramp_down
                        workdays_per_month = 22
                        steady_phase_month = (workdays_per_month * 24 * HOUR) - ramp_up_seconds - ramp_down_seconds
                        month_batches = int(batches_per_second * steady_phase_month + batches_completed_in_rampdown)
                        month_note = f"Continuous {workdays_per_month}-day production, one ramp-up at start, one ramp-down at end"
                        
                        # Year: weeks_per_year weeks
                        # Each week is continuous, but weeks are separate (weekend breaks)
                        year_batches = production_weeks_per_year * week_batches
                        year_note = f"{production_weeks_per_year} continuous work weeks, each week has one ramp-up and one ramp-down"
                    else:
                        # Non-continuous production - each day is separate
                        # Week = days_per_week × day_batches (each day separate)
                        week_batches = days_per_week * day_batches
                        week_note = f"{days_per_week} separate workdays, each with ramp-up and ramp-down"
                        
                        # Month = 22 workdays × day_batches
                        workdays_per_month = 22
                        month_batches = workdays_per_month * day_batches
                        month_note = f"{workdays_per_month} separate workdays, each with ramp-up and ramp-down"
                        
                        # Year = weeks_per_year × week_batches
                        year_batches = production_weeks_per_year * week_batches
                        year_note = f"{production_weeks_per_year} work weeks ({days_per_week} days each), each day with ramp-up and ramp-down"
                    
                    scaled_production = {
                        "calculation_method": calculation_method,
                        "batches_per_hour": round(batches_per_second * HOUR, 2),
                        "ramp_up_time_seconds": ramp_up_seconds,
                        "ramp_down_time_seconds": ramp_down_seconds,
                        "shift": {
                            "duration_hours": shift_duration_hours,
                            "total_batches": shift_batches,
                            "by_product": {},
                            "note": "Single shift with ramp-up and ramp-down"
                        },
                        "day": {
                            "shifts": shifts_per_day,
                            "total_batches": day_batches,
                            "by_product": {},
                            "note": day_note
                        },
                        "week": {
                            "days": days_per_week,
                            "total_batches": week_batches,
                            "by_product": {},
                            "note": week_note
                        },
                        "month": {
                            "days": workdays_per_month,
                            "total_batches": month_batches,
                            "by_product": {},
                            "note": month_note
                        },
                        "year": {
                            "weeks": production_weeks_per_year,
                            "total_batches": year_batches,
                            "by_product": {},
                            "note": year_note
                        }
                    }
                    
                    # Calculate per-product throughput using ORIGINAL target distribution from customer.json
                    # (not the simulated distribution from production.csv)
                    if total_target_quantity > 0:
                        for product_id, target_qty in product_targets.items():
                            product_info = products_dict.get(product_id, {})
                            product_name = product_info.get("name", product_id)
                            pieces_per_batch = product_info.get("pieces_per_batch", 1)
                            product_ratio = target_qty / total_target_quantity
                            
                            # Calculate batches for each period
                            shift_batches = int(scaled_production["shift"]["total_batches"] * product_ratio)
                            day_batches = int(scaled_production["day"]["total_batches"] * product_ratio)
                            week_batches = int(scaled_production["week"]["total_batches"] * product_ratio)
                            month_batches = int(scaled_production["month"]["total_batches"] * product_ratio)
                            year_batches = int(scaled_production["year"]["total_batches"] * product_ratio)
                            
                            scaled_production["shift"]["by_product"][product_id] = {
                                "name": product_name,
                                "batches": shift_batches,
                                "pieces": shift_batches * pieces_per_batch
                            }
                            scaled_production["day"]["by_product"][product_id] = {
                                "name": product_name,
                                "batches": day_batches,
                                "pieces": day_batches * pieces_per_batch
                            }
                            scaled_production["week"]["by_product"][product_id] = {
                                "name": product_name,
                                "batches": week_batches,
                                "pieces": week_batches * pieces_per_batch
                            }
                            scaled_production["month"]["by_product"][product_id] = {
                                "name": product_name,
                                "batches": month_batches,
                                "pieces": month_batches * pieces_per_batch
                            }
                            scaled_production["year"]["by_product"][product_id] = {
                                "name": product_name,
                                "batches": year_batches,
                                "pieces": year_batches * pieces_per_batch
                            }
                    else:
                        print("⚠️  Warning: No product targets found in customer.json - product distribution will be empty")

                    
                    report_data["simulation_info"]["scaled_production_estimates"] = scaled_production
                    
                    # Also add current simulation throughput
                    current_sim_products = {}
                    for product_key, product_data in product_counts.items():
                        current_sim_products[product_key] = {
                            "name": product_data["name"],
                            "batches": product_data["count"]
                        }
                    
                    report_data["simulation_info"]["current_simulation"] = {
                        "total_batches": total_batches,
                        "by_product": current_sim_products,
                        "duration_hours": report_data["simulation_info"]["simulation_duration_hours"]
                    }
                    
            else:
                # No batch data found
                report_data["simulation_info"]["ramp_up_time_seconds"] = 0
                report_data["simulation_info"]["steady_state_time_seconds"] = 0
                report_data["simulation_info"]["ramp_down_time_seconds"] = 0
                report_data["simulation_info"]["ramp_up_time"] = "00:00:00"
                report_data["simulation_info"]["steady_state_time"] = "00:00:00"
                report_data["simulation_info"]["ramp_down_time"] = "00:00:00"
                report_data["simulation_info"]["total_production_time"] = "00:00:00"
                report_data["simulation"]["duration_seconds"] = 0
                report_data["simulation"]["total_batches"] = 0
        else:
            # Directory doesn't exist
            report_data["simulation_info"]["ramp_up_time_seconds"] = 0
            report_data["simulation_info"]["steady_state_time_seconds"] = 0
            report_data["simulation_info"]["ramp_down_time_seconds"] = 0
            report_data["simulation_info"]["ramp_up_time"] = "00:00:00"
            report_data["simulation_info"]["steady_state_time"] = "00:00:00"
            report_data["simulation_info"]["ramp_down_time"] = "00:00:00"
            report_data["simulation_info"]["total_production_time"] = "00:00:00"
            report_data["simulation"]["duration_seconds"] = 0
            report_data["simulation"]["total_batches"] = 0
            
    except Exception as e:
        print(f"Warning: Could not calculate production phase times: {e}")
        report_data["simulation_info"]["ramp_up_time_seconds"] = 0
        report_data["simulation_info"]["steady_state_time_seconds"] = 0
        report_data["simulation_info"]["ramp_down_time_seconds"] = 0
        report_data["simulation_info"]["ramp_up_time"] = "00:00:00"
        report_data["simulation_info"]["steady_state_time"] = "00:00:00"
        report_data["simulation_info"]["ramp_down_time"] = "00:00:00"
        report_data["simulation_info"]["total_production_time"] = "00:00:00"
        report_data["simulation"]["duration_seconds"] = 0
        report_data["simulation"]["total_batches"] = 0
    
    # Add target cycle time from goals.json (outside the try block)
    if target_cycle_time_seconds is not None:
        report_data["simulation"]["target_cycle_time_seconds"] = round(target_cycle_time_seconds, 2)
    
    # --- Transporter Statistics (Hoist Utilization) ---
    # Calculate transporter phase times from movement logs
    try:
        logs_dir = os.path.join(output_dir, "logs")
        movement_file = os.path.join(logs_dir, "transporters_movement.csv")
        
        if os.path.exists(movement_file):
            df = pd.read_csv(movement_file)
            
            # Ensure required columns exist
            required_cols = ['Transporter', 'Phase', 'Start_Time', 'End_Time']
            if all(col in df.columns for col in required_cols):
                # Convert to numeric
                df['Start_Time'] = pd.to_numeric(df['Start_Time'], errors='coerce')
                df['End_Time'] = pd.to_numeric(df['End_Time'], errors='coerce')
                df['Phase'] = pd.to_numeric(df['Phase'], errors='coerce')
                
                # Remove rows with NaN values
                df = df.dropna(subset=['Transporter', 'Phase', 'Start_Time', 'End_Time'])
                
                # Process each transporter
                for transporter in sorted(df['Transporter'].unique()):
                    transporter_df = df[df['Transporter'] == transporter].copy()
                    
                    # Find first phase 2 start and last phase 4 end
                    phase_2_starts = transporter_df[transporter_df['Phase'] == 2]['Start_Time']
                    phase_4_ends = transporter_df[transporter_df['Phase'] == 4]['End_Time']
                    
                    if len(phase_2_starts) == 0 or len(phase_4_ends) == 0:
                        continue  # Skip if no phase 2 or 4
                    
                    first_phase_2_start = phase_2_starts.min()
                    last_phase_4_end = phase_4_ends.max()
                    
                    # Filter only this time period
                    period_df = transporter_df[
                        (transporter_df['Start_Time'] >= first_phase_2_start) &
                        (transporter_df['End_Time'] <= last_phase_4_end)
                    ]
                    
                    # Calculate phase sums
                    phase_sums = {}
                    for phase in [0, 1, 2, 3, 4]:
                        phase_data = period_df[period_df['Phase'] == phase]
                        total_duration = (phase_data['End_Time'] - phase_data['Start_Time']).sum()
                        phase_sums[f'phase_{phase}_seconds'] = int(total_duration)
                    
                    # Total time
                    total_time = last_phase_4_end - first_phase_2_start
                    
                    # Calculate utilization (percentage of non-idle time)
                    idle_time = phase_sums.get('phase_0_seconds', 0)
                    working_time = total_time - idle_time
                    utilization = (working_time / total_time * 100) if total_time > 0 else 0
                    
                    transporter_stat = {
                        'transporter_id': int(transporter),
                        'total_time_seconds': int(total_time),
                        'utilization_percent': round(utilization, 2),
                        'idle_time_seconds': idle_time,
                        'working_time_seconds': int(working_time),
                        **phase_sums
                    }
                    
                    report_data["transporter_statistics"].append(transporter_stat)
                
                # --- Calculate average time per batch for each transporter ---
                # This shows how much time each transporter spends on average per batch (active phases only)
                df['PhaseDuration'] = df['End_Time'] - df['Start_Time']
                active_phases = df[df['Phase'].isin([1, 2, 3, 4])].copy()
                
                if not active_phases.empty and 'Batch' in active_phases.columns:
                    # Sum occupation time per transporter-batch pair
                    batch_occupation = active_phases.groupby(['Transporter', 'Batch'])['PhaseDuration'].sum().reset_index()
                    batch_occupation.rename(columns={'PhaseDuration': 'TotalOccupationTime'}, inplace=True)
                    
                    # Calculate average occupation time per batch for each transporter
                    avg_occupation = batch_occupation.groupby('Transporter')['TotalOccupationTime'].mean().reset_index()
                    avg_occupation.rename(columns={'TotalOccupationTime': 'AvgOccupationPerBatch'}, inplace=True)
                    
                    # Add to transporter statistics
                    for stat in report_data["transporter_statistics"]:
                        t_id = stat['transporter_id']
                        avg_row = avg_occupation[avg_occupation['Transporter'] == t_id]
                        if not avg_row.empty:
                            avg_seconds = avg_row.iloc[0]['AvgOccupationPerBatch']
                            stat['avg_time_per_batch_seconds'] = round(avg_seconds, 2)
                            stat['avg_time_per_batch_minutes'] = round(avg_seconds / 60, 2)
                
                print(f"✅ Transporter statistics calculated for {len(report_data['transporter_statistics'])} transporters")
            else:
                print(f"⚠️  Warning: Missing required columns in {movement_file}")
        else:
            print(f"⚠️  Warning: Movement file not found: {movement_file}")
    except Exception as e:
        print(f"⚠️  Warning: Could not calculate transporter statistics: {e}")
    
    # --- File References ---
    # Store relative paths to key data files from output_dir
    # These are the source data files that contain the actual simulation results
    
    # CP-SAT optimization results
    batch_schedule = os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv')
    if os.path.exists(batch_schedule):
        report_data["files"]["batch_schedule"] = "cp_sat/cp_sat_batch_schedule.csv"
    
    hoist_schedule = os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv')
    if os.path.exists(hoist_schedule):
        report_data["files"]["hoist_schedule"] = "cp_sat/cp_sat_hoist_schedule.csv"
    
    station_schedule = os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv')
    if os.path.exists(station_schedule):
        report_data["files"]["station_schedule"] = "cp_sat/cp_sat_station_schedule.csv"
    
    # Initialization data
    production_csv = os.path.join(init_dir, 'production.csv')
    if os.path.exists(production_csv):
        report_data["files"]["production"] = "initialization/production.csv"
    
    customer_json = os.path.join(init_dir, 'customer.json')
    if os.path.exists(customer_json):
        report_data["files"]["customer"] = "initialization/customer.json"
    
    stations_csv = os.path.join(init_dir, 'stations.csv')
    if os.path.exists(stations_csv):
        report_data["files"]["stations"] = "initialization/stations.csv"
    
    # Log files
    logs_dir_path = os.path.join(output_dir, 'logs')
    movement_file = os.path.join(logs_dir_path, 'transporters_movement.csv')
    if os.path.exists(movement_file):
        report_data["files"]["transporters_movement"] = "logs/transporters_movement.csv"
    
    # --- Capacity Constraints (Cycle Time Bottlenecks) ---
    # Calculate three key constraints that limit production cycle time
    capacity_constraints = {
        "description": "Three primary constraints that limit production cycle time and determine capacity visualization",
        "constraints": {}
    }
    
    # 1. Transporter constraint: longest avg_time_per_batch from any transporter
    transporter_constraint = 0
    transporter_name = None
    if report_data.get("transporter_statistics"):
        for trans_stat in report_data["transporter_statistics"]:
            avg_time_minutes = trans_stat.get("avg_time_per_batch_minutes", 0)
            avg_time_seconds = avg_time_minutes * 60
            if avg_time_seconds > transporter_constraint:
                transporter_constraint = avg_time_seconds
                transporter_name = trans_stat.get("transporter")
    
    capacity_constraints["constraints"]["transporter_limitation"] = {
        "cycle_time_seconds": round(transporter_constraint, 2),
        "cycle_time_minutes": round(transporter_constraint / 60, 2),
        "limiting_transporter": transporter_name,
        "description": "Longest average time per batch from any transporter (transporter capacity bottleneck)"
    }
    
    # 2. Station constraint: longest minimum_cycle_time from any treatment program step
    station_constraint = 0
    station_program = None
    station_stage = None
    if report_data.get("treatment_programs", {}).get("programs"):
        for prog_id, prog_data in report_data["treatment_programs"]["programs"].items():
            for step in prog_data.get("steps", []):
                min_cycle = step.get("minimum_cycle_time_seconds", 0)
                if min_cycle > station_constraint:
                    station_constraint = min_cycle
                    station_program = prog_id
                    station_stage = step.get("stage")
    
    capacity_constraints["constraints"]["station_limitation"] = {
        "cycle_time_seconds": round(station_constraint, 2),
        "cycle_time_minutes": round(station_constraint / 60, 2),
        "limiting_program": station_program,
        "limiting_stage": station_stage,
        "description": "Longest minimum cycle time from any treatment program step (station capacity bottleneck)"
    }
    
    # 3. Container constraint: longest program maximum throughput / available_containers
    container_constraint = 0
    container_program = None
    max_program_throughput = 0
    available_containers = report_data.get("simulation_info", {}).get("available_containers", 50)
    
    if report_data.get("treatment_programs", {}).get("programs"):
        for prog_id, prog_data in report_data["treatment_programs"]["programs"].items():
            max_throughput = prog_data.get("total_maximum_throughput_seconds", 0)
            if max_throughput > max_program_throughput:
                max_program_throughput = max_throughput
                container_program = prog_id
    
    if available_containers > 0 and max_program_throughput > 0:
        container_constraint = max_program_throughput / available_containers
    
    capacity_constraints["constraints"]["container_limitation"] = {
        "cycle_time_seconds": round(container_constraint, 2),
        "cycle_time_minutes": round(container_constraint / 60, 2),
        "available_containers": available_containers,
        "limiting_program": container_program,
        "limiting_program_max_throughput_seconds": round(max_program_throughput, 2),
        "description": f"Longest program maximum throughput divided by available containers (WIP capacity constraint)",
        "calculation": f"{max_program_throughput:.2f}s / {available_containers} containers = {container_constraint:.2f}s per batch"
    }
    
    # Summary: which constraint is the bottleneck?
    constraints_list = [
        ("transporter", transporter_constraint),
        ("station", station_constraint),
        ("container", container_constraint)
    ]
    bottleneck = max(constraints_list, key=lambda x: x[1])
    
    capacity_constraints["bottleneck"] = {
        "type": bottleneck[0],
        "cycle_time_seconds": round(bottleneck[1], 2),
        "cycle_time_minutes": round(bottleneck[1] / 60, 2),
        "description": f"The {bottleneck[0]} limitation is the primary bottleneck (longest cycle time)"
    }
    
    capacity_constraints["visualization_note"] = "These three constraints determine the triangle points in capacity_background.png visualization"
    
    report_data["capacity_constraints"] = capacity_constraints
    
    # Save report data to JSON
    report_data_path = os.path.join(reports_dir, 'report_data.json')
    with open(report_data_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Report data collected: {report_data_path}")
    return report_data_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        collect_report_data(output_dir)
    else:
        print("Usage: python collect_report_data.py <output_dir>")
