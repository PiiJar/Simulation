#!/usr/bin/env python3
"""
Testiputki - VAIHE 4: Visualisoi alkuperäinen line-matriisi

Tekee vain yhden vaiheen:
1. Lukee line_matrix_original.csv simulaatiokansiosta
2. Luo timeline-visualisoinnin näyttäen erien liikkumisen asemien kautta
3. Tallentaa visualisoinnin Logs-kansioon
4. Näyttää tilastoja matriisista
5. Kirjaa tapahtumat simulation_log.csv:hen
"""

import os
import sys
from datetime import datetime

# Lisää projektin juuri Python-polkuun
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import timeline visualization
from visualize_original_matrix import visualize_original_matrix
from generate_tasks import *
from test_step1 import SimulationLogger

def append_to_log(output_dir, log_type, description):
    """Lisää merkinnän simulation_log.csv:hen"""
    log_file = os.path.join(output_dir, "logs", "simulation_log.csv")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},{log_type},{description}\n")

def test_step_4(output_dir):
    """
    VAIHE 4: Visualisoi alkuperäinen line-matriisi timeline-muodossa
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 4 - ALKUPERÄISEN MATRIISIN VISUALISOINTI - ALKAA")
    try:
        # Tarkista että tarvittavat tiedostot löytyvät
        matrix_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
        if not os.path.exists(matrix_file):
            error_msg = f"Original matrix file not found: {matrix_file}"
            raise FileNotFoundError(error_msg)
        
        # Alusta logger ennen visualisointia
        from simulation_logger import init_logger
        init_logger(output_dir)
        
        visualization_file = visualize_original_matrix(output_dir)
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 4 - ALKUPERÄISEN MATRIISIN VISUALISOINTI - VALMIS")
        return visualization_file
    except Exception as e:
        print(f"❌ VIRHE vaiheessa 4: {e}")
        raise

if __name__ == "__main__":
    import argparse
    import glob
    parser = argparse.ArgumentParser(description="VAIHE 4: Visualisoi alkuperäinen line-matriisi")
    parser.add_argument("--output_dir", required=False, help="Simulaatiokansion polku")
    args = parser.parse_args()
    output_dir = args.output_dir

    # Etsi output-kansio aina skriptin sijainnista riippumatta
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_base = os.path.join(script_dir, "output")
        subdirs = [d for d in glob.glob(os.path.join(output_base, "*")) if os.path.isdir(d)]
        if subdirs:
            output_dir = max(subdirs, key=os.path.getmtime)
            # Poistettu ylimääräinen print
        else:
            # Poistettu ylimääräinen print
            sys.exit(1)
    else:
        # Jos annettu output_dir ei ole absoluuttinen, tee siitä absoluuttinen skriptin juureen
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)

    if not os.path.isdir(output_dir):
        print(f"Virhe: Annettua output_dir-kansiota ei löydy: {output_dir}")
        sys.exit(1)

    test_step_4(output_dir)
    print("\nSeuraava vaihe: Venytä tehtävät komennolla:")
    print(f"python test_step5.py --output_dir {output_dir}")
