# Palauttaa viimeisimmän OPTIMIZATION_STATUS-rivin statuksen lokitiedostosta
def get_last_optimization_status(output_dir):
    import os
    log_path = os.path.join(output_dir, "logs", "simulation_log.csv")
    if not os.path.exists(log_path):
        return None
    status = None
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if ",OPTIMIZATION_STATUS," in line:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    status = parts[2].strip().lower()
    return status
"""
Simulation Logger Module
Handles logging of all simulation phases and calculations
Creates and maintains log_classes.csv in the Logs directory
"""

import csv
import os
from datetime import datetime

class SimulationLogger:
    def __init__(self, output_dir):
        """Initialize the simulation logger"""
        self.output_dir = output_dir
        self.log_file = os.path.join(output_dir, "logs", "simulation_log.csv")
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Initialize the log file with headers
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("Timestamp,Type,Description\n")
    
    def log(self, class_type, description):
        """Log an event with timestamp, class and description"""
        # Muutetaan class_type aina isoiksi kirjaimiksi
        class_type = str(class_type).upper()
        # Millisekunnin tarkkuus: kolme desimaalia
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{class_type},{description}\n")
    
    # Convenience methods for different types of logs
    def log_phase(self, description):
        """Log a simulation phase event"""
        self.log('SIM_PHASE', description)
        # Ei tulosteta terminaaliin - käytetään vain tiedostoon tallennukseen
    
    def log_calc(self, description):
        """Log a calculation event"""
        self.log('SIM_CALC', description)
    
    def log_data(self, description):
        """Log a data processing event"""
        self.log('SIM_DATA', description)
    
    def log_io(self, description):
        """Log a file I/O event"""
        self.log('SIM_IO', description)
    
    def log_opt(self, description):
        """Log an optimization event"""
        self.log('SIM_OPT', description)
    
    def log_error(self, description):
        """Log an error event"""
        self.log('SIM_ERROR', description)
    
    def log_viz(self, description):
        """Log a visualization event"""
        self.log('SIM_VIZ', description)
    
    def log_optimization(self, description):
        """Alias for log_opt for compatibility"""
        print(description)
        self.log_opt(description)

# Global logger instance (will be initialized in main.py)
logger = None

def init_logger(output_dir):
    """Initialize the global logger instance"""
    global logger
    logger = SimulationLogger(output_dir)
    # Poistettu ylimääräinen viesti
    return logger

def get_logger():
    """Get the current logger instance"""
    return logger
