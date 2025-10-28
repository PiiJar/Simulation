import pandas as pd
import matplotlib.pyplot as plt
import os
from simulation_logger import get_logger

def visualize_matrix_original(output_dir="output"):
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    # STEP-tyyppinen loggaus
    logs_dir = os.path.join(output_dir, "logs")
    log_file = os.path.join(logs_dir, "simulation_log.csv")
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},STEP,STEP 4 STARTED: VISUALIZING ORIGINAL MATRIX\n")
    print("STEP 4 STARTED: VISUALIZING ORIGINAL MATRIX")
    # ...existing code...
    # Tallenna kuva
    comparison_file = os.path.join(output_dir, "routes_comparison_clean.png")
    plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
    logger.log_viz(f"Comparison visualization saved: {comparison_file}")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},STEP,STEP 4 COMPLETED: VISUALIZING ORIGINAL MATRIX\n")
    print("STEP 4 COMPLETED: VISUALIZING ORIGINAL MATRIX")
    # plt.show() jätetään pois automaattiajossa

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    visualize_matrix_original(output_dir)
