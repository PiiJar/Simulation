#!/usr/bin/env python3
"""
Testiputki - VAIHE 1: Luo simulaatiokansio ja kopioi Initialization

Tekee vain yhden vaiheen:
1. Luo aikaleimattu output-kansio
2. Kopioi Initialization-kansio sinne
3. Luo Logs-kansio
4. Aloittaa lokin kirjoituksen
"""

import os
import sys
from datetime import datetime

# Lisää projektin juuri Python-polkuun
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Tuo vain tarvittava moduuli
from create_simulation_directory import create_simulation_directory

class SimulationLogger:
    def __init__(self, output_dir):
        self.log_file = os.path.join(output_dir, "Logs", "simulation_log.csv")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("Timestamp,Type,Description\n")
    def log(self, log_type, description):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{log_type},{description}\n")

def test_step_1():
    """
    VAIHE 1: Luo simulaatiokansio ja aloita loki
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 1 - SIMULAATIOKANSIOIDEN LUONTI - ALKAA")
    try:
        output_dir = create_simulation_directory()
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 1 - SIMULAATIOKANSIOIDEN LUONTI - VALMIS")
        return output_dir
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {e}")
        import traceback
        #
        return None

if __name__ == "__main__":
    import argparse
    import glob
    parser = argparse.ArgumentParser(description="VAIHE 1: Luo simulaatiokansio ja kopioi Initialization")
    parser.add_argument("--output_dir", required=False, help="Simulaatiokansion polku (valinnainen, luodaan jos puuttuu)")
    args = parser.parse_args()
    output_dir = args.output_dir

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_base = os.path.join(script_dir, "output")
        subdirs = [d for d in glob.glob(os.path.join(output_base, "*")) if os.path.isdir(d)]
        if subdirs:
            output_dir = max(subdirs, key=os.path.getmtime)
        else:
            output_dir = None
    else:
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)

    if output_dir:
        tulos = test_step_1()  # Luo uusi, jos output_dir puuttui
        if tulos:
            output_dir = tulos
    else:
        print("Virhe: output_dir-parametria ei annettu eikä output-kansiota löytynyt.")
        sys.exit(1)
