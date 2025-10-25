#!/usr/bin/env python3
"""
Optimoinnin Visualisointi Proto - Pääskripti

Suorittaa tuotantolinjan simulaatioputken:
1. Simulaatiokansion luonti
2. Käsittelyohjelmien luonti  
3. Alkuperäisen matriisin luonti (fysiikka + optimointi)
4. Alkuperäisen matriisin visualisointi
5. Nostimien tehtävien käsittely (venytys ja optimointi)
6. Muokatun matriisin visualisointi
7. Raporttien muodostus

Optimointi hoidetaan vaiheessa 5 (stretch_transporter_tasks)
"""

from create_simulation_directory import create_simulation_directory
from test_step3 import generate_matrix_step3
from test_step4 import test_step_4
from generate_tasks import generate_tasks
from order_tasks import order_tasks
from stretch_transporter_tasks import stretch_tasks
from visualize_stretched_matrix import visualize_stretched_matrix
from generate_matrix_stretched import generate_matrix_stretched
from resolve_station_conflicts import resolve_station_conflicts
from test_step2 import create_original_programs
from test_step1 import test_step_1
from test_step2 import test_step_2
from test_step3 import test_step_3
from test_step4 import test_step_4
from test_step5 import test_step_5
from test_step6 import test_step_6
from test_step7 import test_step_7
from extract_transporter_tasks import extract_transporter_tasks
from generate_transporters_movement import generate_transporters_movement
from config import USE_CPSAT_OPTIMIZATION
import os

def test_main():
    """
    Suorittaa simulaattorilogiikan vaiheet 1–7:
    """
    # VAIHE 1: Simulaatiokansion luonti
    output_dir = test_step_1()

    # VAIHE 2: Käsittelyohjelmien luonti
    test_step_2(output_dir)

    # VAIHE 2.5: Kopioi original_programs optimized_programs-kansioon
    from copy_originals_to_stretched import copy_originals_to_optimized
    copy_originals_to_optimized(output_dir)

    # Preprocessing: yhdistä ja esikäsittele data CP-SAT:lle
    from preprocess_for_cpsat import preprocess_for_cpsat
    preprocess_for_cpsat(output_dir)

    # CP-SAT optimointi esikäsitellylle datalle
    from run_cpsat_optimization import run_cpsat_optimization
    run_cpsat_optimization(output_dir)
    # Lopetetaan pipeline tähän, jotta tuloksia voidaan tutkia rauhassa.
    return

if __name__ == "__main__":
    test_main()
