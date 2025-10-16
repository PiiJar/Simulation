#!/usr/bin/env python3
"""
Testiputki - VAIHE 6: Visualisoi venytetty matriisi

Tämä vaihe piirtää venytetyn line-matriisin visualisoinnin (timeline),
käyttäen venytettyjä transporter-tehtäviä.

Käyttö:
    python test_step6.py --output_dir <simulaatiokansion polku>

Voidaan kutsua myös test_main.py:stä funktiolla test_step6_visualize_stretched_matrix(output_dir)
"""

import os
import sys
from datetime import datetime
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from visualize_stretched_matrix import visualize_stretched_matrix
from simulation_logger import init_logger
from generate_matrix_stretched import generate_matrix_stretched
from create_sorted_line_matrix import create_sorted_line_matrix

def test_step_6(output_dir):
    """
    VAIHE 6: Visualisoi muokatun (venytetyn) line-matriisin timeline-muodossa
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 6 - MUOKATUN MATRIISIN VISUALISOINTI - ALKAA")
    # Alusta logger
    from simulation_logger import init_logger
    init_logger(output_dir)
    try:
        # Käytä optimoitua matriisia jos on saatavilla
        matrix_file = os.path.join(output_dir, "Logs", "line_matrix_stretched.csv")
        if not os.path.exists(matrix_file):
            generate_matrix_stretched(output_dir)
        
        create_sorted_line_matrix(output_dir)
        
        # Käytä optimoituja nostinliikkeitä jos saatavilla  
        movement_file = os.path.join(output_dir, "Logs", "transporters_movement.csv")
        if not os.path.exists(movement_file):
            # Luo transporter_tasks_final.csv ennen liiketiedoston muodostusta
            from generate_transporter_tasks import create_transporter_tasks_final
            create_transporter_tasks_final(output_dir)
            from generate_transporters_movement import generate_transporters_movement
            generate_transporters_movement(output_dir)
        
        vis_file = visualize_stretched_matrix(output_dir)
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 6 - MUOKATUN MATRIISIN VISUALISOINTI - VALMIS")
        return vis_file
    except Exception as e:
        print(f"❌ VIRHE vaiheessa 6: {e}")
        raise

if __name__ == "__main__":
    import argparse
    import glob
    parser = argparse.ArgumentParser(description="VAIHE 6: Visualisoi venytetty line-matriisi")
    parser.add_argument("--output_dir", required=False, help="Simulaatiokansion polku")
    args = parser.parse_args()
    output_dir = args.output_dir

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
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)

    if not os.path.isdir(output_dir):
        # Poistettu ylimääräinen print
        sys.exit(1)

    test_step_6(output_dir)
    # Poistettu ylimääräiset printit
