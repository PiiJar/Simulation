"""
Collect all simulation data into a single JSON file for reporting.

This module gathers simulation metadata, statistics, and file paths
into a centralized report_data.json file that can be used by report generators.
"""

import os
import json
from datetime import datetime
from load_customer_json import load_customer_json


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
        "files": {},
        "batch_statistics": [],
        "transporter_statistics": [],
        "station_utilization": []
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
    if os.path.exists(goals_path):
        try:
            with open(goals_path, 'r') as f:
                goals = json.load(f)
                report_data["simulation_info"]["simulation_duration_hours"] = goals.get("simulation_duration_hours", 0.0)
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
        
        if os.path.exists(production_path):
            df_production = pd.read_csv(production_path)
            total_batches = len(df_production)
            
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
                
                # Find first batch's last stage entry time (ramp-up end)
                # Last stage = highest stage number for batch 1
                first_batch = df_schedule[df_schedule['Batch'] == df_schedule['Batch'].min()]
                last_stage_of_first = first_batch[first_batch['Stage'] == first_batch['Stage'].max()].iloc[0]
                ramp_up_end = last_stage_of_first['EntryTime']
                
                # Find when last batch started (ramp-down start)
                # First stage entry of last batch
                last_batch_num = df_schedule['Batch'].max()
                last_batch = df_schedule[df_schedule['Batch'] == last_batch_num]
                first_stage_of_last = last_batch[last_batch['Stage'] == last_batch['Stage'].min()].iloc[0]
                ramp_down_start = first_stage_of_last['EntryTime']
                
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
                
                # --- Production Throughput Calculations ---
                # Calculate scaled production estimates for different time periods
                # Total production = steady_state + ramp_down completions
                if total_batches > 0 and ramp_down_end > 0:
                    
                    # For throughput calculations, use steady-state period if it exists
                    if report_data["simulation_info"]["has_steady_state"]:
                        # Count batches completed during steady state (pure throughput rate)
                        steady_state_duration = ramp_down_start - ramp_up_end
                        batches_completed_in_steady = 0
                        
                        # Count batches completed during ramp-down (work in progress completion)
                        batches_completed_in_rampdown = 0
                        
                        for batch in df_schedule['Batch'].unique():
                            batch_data = df_schedule[df_schedule['Batch'] == batch]
                            last_stage = batch_data['Stage'].max()
                            last_stage_data = batch_data[batch_data['Stage'] == last_stage]
                            
                            if not last_stage_data.empty:
                                exit_time = last_stage_data.iloc[0]['ExitTime']
                                
                                # Completed in steady state
                                if ramp_up_end < exit_time <= ramp_down_start:
                                    batches_completed_in_steady += 1
                                # Completed in ramp-down
                                elif exit_time > ramp_down_start:
                                    batches_completed_in_rampdown += 1
                        
                        if batches_completed_in_steady > 0 and steady_state_duration > 0:
                            batches_per_second = batches_completed_in_steady / steady_state_duration
                            calculation_method = "steady_state_with_rampdown"
                            
                            report_data["simulation_info"]["steady_state_batches_completed"] = batches_completed_in_steady
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
        else:
            # Directory doesn't exist
            report_data["simulation_info"]["ramp_up_time_seconds"] = 0
            report_data["simulation_info"]["steady_state_time_seconds"] = 0
            report_data["simulation_info"]["ramp_down_time_seconds"] = 0
            report_data["simulation_info"]["ramp_up_time"] = "00:00:00"
            report_data["simulation_info"]["steady_state_time"] = "00:00:00"
            report_data["simulation_info"]["ramp_down_time"] = "00:00:00"
            report_data["simulation_info"]["total_production_time"] = "00:00:00"
            
    except Exception as e:
        print(f"Warning: Could not calculate production phase times: {e}")
        report_data["simulation_info"]["ramp_up_time_seconds"] = 0
        report_data["simulation_info"]["steady_state_time_seconds"] = 0
        report_data["simulation_info"]["ramp_down_time_seconds"] = 0
        report_data["simulation_info"]["ramp_up_time"] = "00:00:00"
        report_data["simulation_info"]["steady_state_time"] = "00:00:00"
        report_data["simulation_info"]["ramp_down_time"] = "00:00:00"
        report_data["simulation_info"]["total_production_time"] = "00:00:00"
    
    # --- File References ---
    # Store relative paths from output_dir
    # Images
    matrix_timeline_1 = os.path.join(reports_dir, 'matrix_timeline_page_1.png')
    if os.path.exists(matrix_timeline_1):
        report_data["files"]["matrix_timeline_page_1"] = "reports/matrix_timeline_page_1.png"
    
    gantt_schedule = os.path.join(output_dir, 'cp_sat', 'schedule_gantt.png')
    if os.path.exists(gantt_schedule):
        report_data["files"]["gantt_schedule"] = "cp_sat/schedule_gantt.png"
    
    # Transporter pie charts
    for i in [1, 2]:
        pie_path = os.path.join(reports_dir, f'transporter_{i}_phases_pie.png')
        if os.path.exists(pie_path):
            report_data["files"][f"transporter_{i}_phases_pie"] = f"reports/transporter_{i}_phases_pie.png"
    
    # CSV files
    treatment_programs_csv = os.path.join(reports_dir, 'treatment_programs.csv')
    if os.path.exists(treatment_programs_csv):
        report_data["files"]["treatment_programs_csv"] = "reports/treatment_programs.csv"
    
    transporter_phases_csv = os.path.join(reports_dir, 'transporter_phases.csv')
    if os.path.exists(transporter_phases_csv):
        report_data["files"]["transporter_phases_csv"] = "reports/transporter_phases.csv"
    
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
