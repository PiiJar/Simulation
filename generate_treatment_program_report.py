#!/usr/bin/env python3
"""
generate_treatment_program_report.py

Luo raportin käytetyistä käsittelyohjelmista simulaatiossa.
Lukee original_programs-kansiosta kaikki ohjelmat ja luo yhteenvetoraportin.

Author: Simulation Pipeline
Version: 1.0
Date: 2025-08-05
"""

import pandas as pd
import os
import glob
from simulation_logger import get_logger


def generate_treatment_program_report(output_dir="output"):
    """
    Luo raportin käytetyistä käsittelyohjelmista simulaatiossa.
    
    Args:
        output_dir: Path to the simulation output directory
        
    Returns:
        str: Path to saved report file
    """
    
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    
    logger.log_data("Treatment program report generation started")
    
    # Paths
    original_programs_dir = os.path.join(output_dir, "original_programs")
    stations_file = os.path.join(output_dir, "initialization", "Stations.csv")
    reports_dir = os.path.join(output_dir, "reports")
    report_file = os.path.join(reports_dir, "treatment_program_report.html")
    
    # Check if directories exist
    if not os.path.exists(original_programs_dir):
        logger.log_error(f"Original programs directory not found: {original_programs_dir}")
        raise FileNotFoundError(f"Original programs directory not found: {original_programs_dir}")
    
    if not os.path.exists(stations_file):
        logger.log_error(f"Stations file not found: {stations_file}")
        raise FileNotFoundError(f"Stations file not found: {stations_file}")
    
    # Load station information
    stations_df = pd.read_csv(stations_file)
    station_names = dict(zip(stations_df['Number'], stations_df['Name']))
    
    # Find all treatment program files
    program_files = glob.glob(os.path.join(original_programs_dir, "*_Treatment_program_*.csv"))
    
    if not program_files:
        logger.log_error("No treatment program files found in original_programs directory")
        raise FileNotFoundError("No treatment program files found in original_programs directory")
    
    # Extract unique program numbers
    program_numbers = set()
    for file_path in program_files:
        filename = os.path.basename(file_path)
        # Extract program number from filename: Batch_XXX_Treatment_program_YYY.csv
        if "_Treatment_program_" in filename:
            program_part = filename.split("_Treatment_program_")[1].replace(".csv", "")
            program_numbers.add(program_part)
    
    logger.log_data(f"Found {len(program_numbers)} unique treatment programs")
    
    # Generate report for each unique program
    all_program_data = []
    
    for program_num in sorted(program_numbers):
        # Find a file with this program number
        matching_files = [f for f in program_files if f"_Treatment_program_{program_num}.csv" in f]
        
        if matching_files:
            program_file = matching_files[0]  # Take the first match
            
            try:
                program_df = pd.read_csv(program_file)
                
                # Process each stage in the program
                for _, row in program_df.iterrows():
                    stage = int(row['Stage'])
                    min_stat = int(row['MinStat'])
                    max_stat = int(row['MaxStat'])
                    
                    # Get station names (käytä min_stat nimeä, koska min ja max ovat samoja)
                    station_name = station_names.get(min_stat, 'Unknown')
                    
                    # Convert times to hh:mm:ss format
                    min_time = pd.to_timedelta(row['MinTime']).total_seconds()
                    max_time = pd.to_timedelta(row['MaxTime']).total_seconds()
                    
                    min_time_str = pd.to_datetime(min_time, unit='s').strftime('%H:%M:%S')
                    max_time_str = pd.to_datetime(max_time, unit='s').strftime('%H:%M:%S')
                    
                    all_program_data.append({
                        'Stage': stage,
                        'Min Station': min_stat,
                        'Max Station': max_stat,
                        'Station Name': station_name,
                        'Min Time': min_time_str,
                        'Max Time': max_time_str
                    })
                    
            except Exception as e:
                logger.log_error(f"Error processing program file {program_file}: {e}")
                continue
    
    if not all_program_data:
        logger.log_error("No program data could be processed")
        raise ValueError("No program data could be processed")
    
    # Create DataFrame and sort by Stage
    report_df = pd.DataFrame(all_program_data)
    report_df = report_df.sort_values(['Stage']).reset_index(drop=True)
    
    # Get simulation directory name
    simulation_name = os.path.basename(os.path.abspath(output_dir))
    
    # Generate HTML report
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Treatment Program Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .program-header {{ background-color: #e8f4f8; font-weight: bold; }}
        .center {{ text-align: center; }}
    </style>
</head>
<body>
    <h1>Used Treatment Programs in Simulation {simulation_name}</h1>
    
    <table>
        <thead>
            <tr>
                <th>Stage</th>
                <th>Min Station</th>
                <th>Max Station</th>
                <th>Station Name</th>
                <th>Min Time</th>
                <th>Max Time</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for _, row in report_df.iterrows():
        html_content += f"""
            <tr>
                <td class="center">{row['Stage']}</td>
                <td class="center">{row['Min Station']}</td>
                <td class="center">{row['Max Station']}</td>
                <td>{row['Station Name']}</td>
                <td class="center">{row['Min Time']}</td>
                <td class="center">{row['Max Time']}</td>
            </tr>
        """
    
    html_content += """
        </tbody>
    </table>
    
    <div style="margin-top: 30px; font-size: 12px; color: #666;">
        <p>Report generated by Simulation Pipeline</p>
        <p>Date: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </div>
</body>
</html>
"""
    
    # Save HTML report
    os.makedirs(reports_dir, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Also save as CSV for data analysis
    csv_report_file = os.path.join(reports_dir, "treatment_program_report.csv")
    report_df.to_csv(csv_report_file, index=False)
    
    logger.log_viz(f"Treatment program report saved: {report_file}")
    logger.log_viz(f"Treatment program CSV saved: {csv_report_file}")
    logger.log_data("Treatment program report generation completed")
    
    return report_file


if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    from simulation_logger import init_logger
    init_logger(output_dir)
    generate_treatment_program_report(output_dir)
