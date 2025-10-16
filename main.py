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
import os

def test_main():
    """
    Suorittaa simulaattorilogiikan vaiheet 1–7:
    """
    try:
        # VAIHE 1: Simulaatiokansion luonti
        output_dir = test_step_1()

        # VAIHE 2: Käsittelyohjelmien luonti
        test_step_2(output_dir)

        # VAIHE 2.5: Kopioi original_programs optimized_programs-kansioon
        from copy_originals_to_stretched import copy_originals_to_optimized
        copy_originals_to_optimized(output_dir)

        # VAIHE 3: Alkuperäisen matriisin luonti
        test_step_3(output_dir)

        # VAIHE 4: Alkuperäisen matriisin visualisointi
        test_step_4(output_dir)

        # VAIHE 5: Nostimien tehtävien käsittely
        test_step_5(output_dir)

        # VAIHE 6: Muokatun matriisin luonti (käyttää aina fysiikkaa)
        generate_matrix_stretched(output_dir)

        # VAIHE 6.1: Erotetaan nostintehtävät LOPULLISESTA matriisista
        tasks_from_matrix = extract_transporter_tasks(output_dir)

        # VAIHE 6.2: Luodaan yksityiskohtaiset nostimien liikkeet
        from extract_transporter_tasks import create_detailed_movements
        detailed_movements = create_detailed_movements(output_dir)

        # VAIHE 6.5: Nostinliikkeiden luonti (optimoiduista tehtävistä)
        generate_transporters_movement(output_dir)

        # VAIHE 7: Muokatun matriisin visualisointi
        test_step_6(output_dir)

        # VAIHE 7: Raporttien muodostus (kuormitusanalyysi + kaikki raportit)
        test_step_7(output_dir)

        # VAIHE 7: Transporter-aikajakaumaraportti (uusi)
        from report_transporter_time_distribution import report_transporter_time_distribution
        report_transporter_time_distribution(output_dir)
    except Exception as e:
        print(f"❌ VIRHE simulaatiossa: {e}")
        return

if __name__ == "__main__":
    test_main()
