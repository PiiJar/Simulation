#!/usr/bin/env python3
"""
gener    # Paths
    production_file = os.path.join(output_dir, "logs", "Production.csv")
    line_matrix_file = os.path.join(output_dir, "logs", "line_matrix_stretched.csv")
    reports_dir = os.path.join(output_dir, "reports")
    report_file = os.path.join(reports_dir, "production_report.html")roduction_report.py

Luo raportin tuotannon läpivirtauksesta simulaatiossa.
Analysoi erien kulkua linjan läpi ja laskee kapasiteettitietoja.

Author: Simulation Pipeline
Version: 1.0
Date: 2025-08-05
"""

import pandas as pd
import os
from simulation_logger import get_logger


def time_to_seconds(time_str):
    """Muunna aika sekunneiksi"""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    time_str = str(time_str).strip()
    if 's' in time_str:
        return float(time_str.replace('s', ''))
    
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    return float(time_str)


def generate_production_report(output_dir="output"):
    """
    Luo raportin tuotannon läpivirtauksesta simulaatiossa.
    
    Args:
        output_dir: Path to the simulation output directory
        
    Returns:
        str: Path to saved report file
    """
    
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    
    logger.log_data("Production report generation started")
    
    # Paths
    production_file = os.path.join(output_dir, "Initialization", "Production.csv")
    matrix_file = os.path.join(output_dir, "logs", "line_matrix_stretched.csv")
    reports_dir = os.path.join(output_dir, "Reports")
    report_file = os.path.join(reports_dir, "production_report.html")
    
    # Check if files exist
    if not os.path.exists(production_file):
        logger.log_error(f"Production file not found: {production_file}")
        raise FileNotFoundError(f"Production file not found: {production_file}")
    
    if not os.path.exists(matrix_file):
        logger.log_error(f"Matrix file not found: {matrix_file}")
        raise FileNotFoundError(f"Matrix file not found: {matrix_file}")
    
    # Load data
    production_df = pd.read_csv(production_file)
    matrix_df = pd.read_csv(matrix_file)
    
    # Convert Start_time to seconds (add the missing column)
    production_df['Start_time_seconds'] = production_df['Start_time'].apply(time_to_seconds)
    
    logger.log_data(f"Found {len(production_df)} batches in production")
    
    # Process each batch
    production_data = []
    
    for _, prod_row in production_df.iterrows():
        batch_id = int(prod_row['Batch'])
        treatment_program = int(prod_row['Treatment_program'])
        loading_station = int(prod_row['Start_station'])
        
        # Convert start time to seconds for calculations
        process_started_seconds = float(prod_row['Start_time_seconds'])
        
        # Find batch data in matrix (last stage for unloading info)
        batch_matrix = matrix_df[matrix_df['Batch'] == batch_id]
        
        if not batch_matrix.empty:
            # Find the last stage (highest Stage number) for this batch
            last_stage = batch_matrix.loc[batch_matrix['Stage'].idxmax()]
            
            unloading_station = int(last_stage['Station'])
            process_finished_seconds = float(last_stage['ExitTime'])
            
            # Calculate total treatment time
            total_treatment_seconds = process_finished_seconds - process_started_seconds
            
            # Convert times to hh:mm:ss format
            process_started_str = pd.to_datetime(process_started_seconds, unit='s').strftime('%H:%M:%S')
            process_finished_str = pd.to_datetime(process_finished_seconds, unit='s').strftime('%H:%M:%S')
            total_treatment_str = pd.to_datetime(total_treatment_seconds, unit='s').strftime('%H:%M:%S')
            
            production_data.append({
                'Batch': batch_id,
                'Treatment Program': treatment_program,
                'Loading Station': loading_station,
                'Process Started': process_started_str,
                'Unloading Station': unloading_station,
                'Process Finished': process_finished_str,
                'Total Treatment Time': total_treatment_str
            })
    
    if not production_data:
        logger.log_error("No production data could be processed")
        raise ValueError("No production data could be processed")
    
    # Create DataFrame
    report_df = pd.DataFrame(production_data)
    
    # Calculate capacity metrics
    if len(production_df) > 1:
        first_batch_start = float(production_df.iloc[0]['Start_time_seconds'])
        last_batch_start = float(production_df.iloc[-1]['Start_time_seconds'])
        
        time_span_seconds = last_batch_start - first_batch_start
        time_span_hours = time_span_seconds / 3600
        
        # Average cycle time = time span / (number of batches - 1)
        num_batches = len(production_df)
        if num_batches > 1:
            avg_cycle_time_seconds = time_span_seconds / (num_batches - 1)
            avg_cycle_time_str = pd.to_datetime(avg_cycle_time_seconds, unit='s').strftime('%H:%M:%S')
            
            # Batches per hour = 3600 / avg_cycle_time_seconds
            batches_per_hour = 3600 / avg_cycle_time_seconds if avg_cycle_time_seconds > 0 else 0
        else:
            avg_cycle_time_str = "N/A"
            batches_per_hour = 0
    else:
        avg_cycle_time_str = "N/A"
        batches_per_hour = 0
    
    # Get simulation directory name
    simulation_name = os.path.basename(os.path.abspath(output_dir))
    
    # Generate HTML report
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Production Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .center {{ text-align: center; }}
        .metrics {{ background-color: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .metrics h3 {{ margin-top: 0; color: #2c3e50; }}
    </style>
</head>
<body>
    <h1>Production Throughput in Simulation {simulation_name}</h1>
    
    <table>
        <thead>
            <tr>
                <th>Batch</th>
                <th>Treatment Program</th>
                <th>Loading Station</th>
                <th>Process Started</th>
                <th>Unloading Station</th>
                <th>Process Finished</th>
                <th>Total Treatment Time</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for _, row in report_df.iterrows():
        html_content += f"""
            <tr>
                <td class="center">{row['Batch']}</td>
                <td class="center">{row['Treatment Program']}</td>
                <td class="center">{row['Loading Station']}</td>
                <td class="center">{row['Process Started']}</td>
                <td class="center">{row['Unloading Station']}</td>
                <td class="center">{row['Process Finished']}</td>
                <td class="center">{row['Total Treatment Time']}</td>
            </tr>
        """
    
    html_content += f"""
        </tbody>
    </table>
    
    <div class="metrics">
        <h3>Production Capacity Metrics</h3>
        <p><strong>Average Batches per hour:</strong> {batches_per_hour:.2f}</p>
        <p><strong>Average Cycle Time:</strong> {avg_cycle_time_str}</p>
    </div>
    
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
    csv_report_file = os.path.join(reports_dir, "production_report.csv")
    
    # Add capacity metrics to CSV
    metrics_df = pd.DataFrame({
        'Metric': ['Average Batches per hour', 'Average Cycle Time'],
        'Value': [f"{batches_per_hour:.2f}", avg_cycle_time_str]
    })
    
    # Save production data and metrics in separate sheets-like format
    with open(csv_report_file, 'w') as f:
        f.write("# Production Throughput Data\\n")
        report_df.to_csv(f, index=False)
        f.write("\\n# Capacity Metrics\\n")
        metrics_df.to_csv(f, index=False)
    
    logger.log_viz(f"Production report saved: {report_file}")
    logger.log_viz(f"Production CSV saved: {csv_report_file}")
    logger.log_data("Production report generation completed")
    
    return report_file


if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    from simulation_logger import init_logger
    init_logger(output_dir)
    generate_production_report(output_dir)
