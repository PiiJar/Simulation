"""
Generate goals.json based on customer.json and plant data, calculating all values anew.
"""
import os
import json
import csv
from load_customer_json import load_customer_json

def generate_goals(output_dir, treatment_programs=None, transfer_times=None):
    """
    Luo goals.json output_dir/initialization/ kansioon customer.jsonin ja muiden lähdedatan pohjalta.
    Luo myös production.csv, jossa batchit jaetaan tavoitteiden mukaan 8 tunnin simulaatioon.
    Aloitusasema valitaan stations.jsonin start_station=True asemista vuorotellen.
    Args:
        output_dir: Path to simulation output directory
        treatment_programs: Optional dict mapping product_id to list of stage minimum times (seconds)
        transfer_times: Optional dict mapping product_id to average transfer time (seconds)
    """
    goals_path = os.path.join(output_dir, "initialization", "goals.json")
    production_path = os.path.join(output_dir, "initialization", "production.csv")
    stations_path = os.path.join(output_dir, "initialization", "stations.json")
    customer_json_dir = os.path.join(output_dir, "initialization")
    # Load customer.json
    try:
        _, plant, products = load_customer_json(customer_json_dir)
    except Exception as e:
        print(f"Error loading customer.json: {e}")
        return
    # Load stations.json
    try:
        with open(stations_path, "r", encoding="utf-8") as f:
            stations_data = json.load(f)
        start_stations = [s["number"] for s in stations_data["stations"] if s.get("start_station") is True]
        if not start_stations:
            print("No start_station found in stations.json!")
            return
    except Exception as e:
        print(f"Error loading stations.json: {e}")
        return
    # Get valid product_ids from both plant.production_targets.annual and products
    valid_ids = set()
    annual_targets = plant.get("production_targets", {}).get("annual", [])
    for target in annual_targets:
        pid = target.get("product_id")
        if pid:
            valid_ids.add(pid)
    product_map = {prod.get("id"): prod for prod in products}
    # Calculate total annual target for share calculation
    total_annual = sum([target.get("target_quantity", 0) for target in annual_targets if target.get("product_id") in valid_ids])
    # Simulation/plant context
    available_containers = plant.get("available_containers", 50)  # Default 50 if not specified
    weeks_per_year = plant.get("production_schedule", {}).get("weeks_per_year", 48)
    days_per_week = plant.get("production_schedule", {}).get("days_per_week", 5)
    shifts_per_day = plant.get("production_schedule", {}).get("shifts_per_day", 2)
    hours_per_shift = plant.get("production_schedule", {}).get("hours_per_shift", 8.0)
    working_days_per_year = weeks_per_year * days_per_week
    total_annual_hours = working_days_per_year * shifts_per_day * hours_per_shift
    simulation_duration_hours = 8.0  # lyhennetty simulaatio
    # Build product_targets and per_product_pace only for valid products
    product_targets = []
    per_product_pace = {}
    production_share_validation = {}
    total_daily_pieces = 0
    total_daily_batches = 0
    batch_counts = {}
    for target in annual_targets:
        pid = target.get("product_id")
        if pid not in valid_ids:
            continue
        prod = product_map.get(pid)
        if not prod:
            continue
        annual_target = target.get("target_quantity", 0)
        pieces_per_batch = prod.get("properties", {}).get("pieces_per_batch", 1)
        treatment_program = prod.get("properties", {}).get("treatment_program", 1)
        
        # Validointi
        if annual_target <= 0:
            raise ValueError(f"Product {pid}: annual_target must be > 0, got {annual_target}")
        if pieces_per_batch <= 0:
            raise ValueError(f"Product {pid}: pieces_per_batch must be > 0, got {pieces_per_batch}")
        
        daily_target_pieces = annual_target / working_days_per_year
        daily_target_batches = daily_target_pieces / pieces_per_batch
        
        # Laske simulaatioajan erien määrä
        simulation_target_batches_float = daily_target_batches * simulation_duration_hours / 24.0
        simulation_target_batches = int(round(simulation_target_batches_float))
        
        # Validointi: ei sallita nollaa eriä
        if simulation_target_batches == 0:
            raise ValueError(
                f"Product {pid}: Simulation results in 0 batches!\n"
                f"  Annual target: {annual_target} pieces\n"
                f"  Daily target: {daily_target_pieces:.2f} pieces ({daily_target_batches:.2f} batches)\n"
                f"  Simulation ({simulation_duration_hours}h): {simulation_target_batches_float:.2f} batches (rounds to 0)\n"
                f"  Solution: Increase annual_target in customer.json or decrease pieces_per_batch"
            )
        
        simulation_target_pieces = simulation_target_batches * pieces_per_batch
        daily_target_pieces_int = int(round(daily_target_pieces))
        daily_target_batches_int = int(round(daily_target_batches))
        
        share = round(100.0 * annual_target / total_annual, 1) if total_annual else 0.0
        # Process time
        min_stage = 0
        transfer = 0
        if treatment_programs and pid in treatment_programs:
            min_stage = sum(treatment_programs[pid])
        if transfer_times and pid in transfer_times:
            transfer = transfer_times[pid]
        minimum_process_time_seconds = min_stage + transfer if (min_stage > 0 or transfer > 0) else None
        process_time_calculated = bool(minimum_process_time_seconds)
        product_targets.append({
            "product_id": pid,
            "product_name": prod.get("name", ""),
            "treatment_program": treatment_program,
            "pieces_per_batch": pieces_per_batch,
            "annual_target": annual_target,
            "production_share_percent": share,
            "daily_target_pieces": daily_target_pieces_int,
            "daily_target_batches": daily_target_batches_int,
            "simulation_target_pieces": simulation_target_pieces,
            "simulation_target_batches": simulation_target_batches,
            "minimum_process_time_seconds": minimum_process_time_seconds,
            "process_time_calculated": process_time_calculated,
            "calculation": {
                "note": f"Annual target {annual_target} pieces / {working_days_per_year} working days = {daily_target_pieces} pieces/day",
                "batches_per_day": f"{daily_target_pieces} pieces / {pieces_per_batch} pieces_per_batch = {daily_target_batches} batches/day",
                "simulation_batches": f"{simulation_duration_hours}h simulation = {daily_target_batches} * {simulation_duration_hours}/24 = {simulation_target_batches} batches",
                "minimum_process_time": "Sum of treatment program minimum stage times + average transfer times (calculated during preprocessing)"
            }
        })
        # Build per_product_pace entry - käytä simulaatioajan erämäärää
        batches_per_hour = round(simulation_target_batches / simulation_duration_hours, 3) if simulation_duration_hours else 0
        avg_interval_min = round(60 / batches_per_hour, 2) if batches_per_hour else None
        avg_interval_sec = round(3600 / batches_per_hour, 2) if batches_per_hour else None
        per_product_pace[pid] = {
            "simulation_batches": simulation_target_batches,
            "batches_per_hour": batches_per_hour,
            "average_interval_minutes": avg_interval_min,
            "average_interval_seconds": avg_interval_sec,
            "calculation": f"{simulation_target_batches} batches / {simulation_duration_hours} hours = {batches_per_hour} batches/hour; 60 min / {batches_per_hour} = {avg_interval_min} min"
        }
        production_share_validation[pid] = f"{share}%"
        total_daily_pieces += daily_target_pieces
        total_daily_batches += daily_target_batches
        batch_counts[pid] = simulation_target_batches  # Käytä simulaatioajan erämäärää!
    production_share_validation["total"] = f"{sum([float(v.strip('%')) for v in production_share_validation.values()]):.1f}%"
    # Target pace (total batches = sum of daily_target_batches for all products)
    total_batches = sum(batch_counts.values())
    batches_per_hour = round(total_batches / simulation_duration_hours, 3) if simulation_duration_hours else 0
    avg_batch_interval_min = round(60 / batches_per_hour, 2) if batches_per_hour else None
    avg_batch_interval_sec = round(3600 / batches_per_hour, 2) if batches_per_hour else None
    
    # Calculate target cycle time based on annual targets (more realistic)
    annual_production_hours = weeks_per_year * days_per_week * shifts_per_day * hours_per_shift
    annual_batches = sum([target.get("target_quantity", 0) / product_map.get(target.get("product_id", {}), {}).get("properties", {}).get("pieces_per_batch", 1) 
                         for target in annual_targets if target.get("product_id") in valid_ids])
    annual_batches_per_hour = annual_batches / annual_production_hours if annual_production_hours > 0 else 0
    target_cycle_time_seconds = round(3600 / annual_batches_per_hour, 2) if annual_batches_per_hour > 0 else None
    
    # Build goals.json structure - vain simulaatiokohtaiset tavoitteet
    goals = {
        "simulation_goals": {
            "description": "Production goals for this simulation run",
            "calculation_basis": "Derived from annual production targets in customer.json",
            "reference": "See customer.json for plant production schedule and annual targets",
            "simulation_period": {
                "duration_hours": simulation_duration_hours,
                "description": f"Simulation represents {simulation_duration_hours} hours of production"
            },
            "plant_constraints": {
                "available_containers": available_containers,
                "description": "Number of transport containers/carriers available for batches"
            }
        },
        "simulation_targets": [
            {
                "product_id": pt["product_id"],
                "product_name": pt["product_name"],
                "treatment_program": pt["treatment_program"],
                "pieces_per_batch": pt["pieces_per_batch"],
                "target_batches": pt["simulation_target_batches"],
                "target_pieces": pt["simulation_target_pieces"],
                "production_share_percent": pt["production_share_percent"]
            }
            for pt in product_targets
        ],
        "totals": {
            "total_simulation_batches": total_batches,
            "production_share_validation": production_share_validation
        },
        "target_pace": {
            "simulation_duration_hours": simulation_duration_hours,
            "total_batches": total_batches,
            "batches_per_hour": batches_per_hour,
            "average_batch_interval_minutes": avg_batch_interval_min,
            "average_batch_interval_seconds": avg_batch_interval_sec,
            "target_cycle_time_seconds": target_cycle_time_seconds,
            "calculation": {
                "batches_per_hour": f"{total_batches} batches / {simulation_duration_hours} hours = {batches_per_hour} batches/hour",
                "interval_minutes": f"60 minutes / {batches_per_hour} batches = {avg_batch_interval_min} minutes/batch",
                "interval_seconds": f"3600 seconds / {batches_per_hour} batches = {avg_batch_interval_sec} seconds/batch",
                "annual_target_cycle_time": f"Annual batches: {annual_batches:.0f}, Annual hours: {annual_production_hours}, Target cycle time: {target_cycle_time_seconds}s"
            },
            "interpretation": {
                "description": f"On average, a new batch should start every {avg_batch_interval_min} minutes to meet daily target",
                "practical_note": "Actual intervals may vary based on treatment program duration and transporter capacity",
                "target_cycle_time_note": f"Target cycle time based on annual production goals: {target_cycle_time_seconds}s per batch"
            },
            "per_product_pace": per_product_pace
        },
        "metadata": {
            "version": "1.0",
            "created": "2025-11-13",
            "description": "Simulation production goals - defines target quantities for simulation period",
            "usage": {
                "initialization": "This file is created during simulation initialization based on customer.json data",
                "location": "Copied to output/{simulation_dir}/initialization/goals.json",
                "purpose": "Defines how many batches of each product to simulate for target period"
            }
        }
    }
    os.makedirs(os.path.dirname(goals_path), exist_ok=True)
    with open(goals_path, "w", encoding="utf-8") as f:
        json.dump(goals, f, indent=2, ensure_ascii=False)
    print(f"Created goals.json from customer.json and plant data.")
    # Luo production.csv
    os.makedirs(os.path.dirname(production_path), exist_ok=True)  # Varmista kansio
    batches = []
    batch_id = 1
    start_station_count = len(start_stations)
    start_station_idx = 0
    for pid, count in batch_counts.items():
        prod = product_map.get(pid)
        program = prod.get("properties", {}).get("treatment_program", 1)
        for _ in range(count):
            station = start_stations[start_station_idx % start_station_count]
            batches.append({
                "Batch": batch_id,
                "Treatment_program": program,
                "Start_station": station,
                "Start_time": "00:00:00",
                "Start_optimized": "00:00:00"
            })
            batch_id += 1
            start_station_idx += 1
    # Kirjoita production.csv oikeilla sarakkeilla
    with open(production_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Batch", "Treatment_program", "Start_station", "Start_time", "Start_optimized"])
        writer.writeheader()
        for row in batches:
            writer.writerow(row)
    print(f"Created production.csv with {len(batches)} batches for {simulation_duration_hours}h simulation.")
