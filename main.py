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

import os
import pandas as pd
from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs_original import generate_batch_treatment_programs_original
from preprocess_for_cpsat import preprocess_for_cpsat

def initialize_simulation(output_dir):
    """
    Alustaa simulaation luomalla tarvittavat kansiot, käsittelyohjelmat ja esikäsittelemällä datan CP-SAT:ia varten.
    """
    # Luo simulaatiokansio
    output_dir = create_simulation_directory()

    # Kopioi initialization-kansio ja kaikki sen sisältö simulaatiokansioon
    import shutil
    init_dir = os.path.join(os.getcwd(), "initialization")
    dst_init = os.path.join(output_dir, "initialization")
    if os.path.exists(dst_init):
        shutil.rmtree(dst_init)
    shutil.copytree(init_dir, dst_init)

    # Esikäsittele data CP-SAT:ia varten (muotoile oikeat tiedostot)
    preprocess_for_cpsat(output_dir)

    return output_dir

def main():
    """
    Suorittaa simulaattorilogiikan vaiheet alusta loppuun.
    """
    try:
        # Alustus ja esikäsittely (tuottaa output_dir)
        output_dir = initialize_simulation("output")

        # Kopioi kaikki tarvittavat syötetiedostot initialize-kansiosta simulaatiokansioon
        import shutil
        init_dir = os.path.join(os.getcwd(), "initialization")
        files_to_copy = [
            "stations.csv",
            "transporters.csv",
            "transfer_tasks.csv",
            "transporters_start_positions.csv",
            "productions.csv",
        ]
        for fname in files_to_copy:
            src = os.path.join(init_dir, fname)
            dst = os.path.join(output_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                raise FileNotFoundError(f"Syötetiedosto puuttuu: {src}. Täytä tämä tiedosto initialize-kansioon.")
        # Kopioi treatment_programs-kansio
        src_tprog = os.path.join(init_dir, "treatment_programs")
        dst_tprog = os.path.join(output_dir, "treatment_programs")
        if os.path.exists(src_tprog):
            if os.path.exists(dst_tprog):
                shutil.rmtree(dst_tprog)
            shutil.copytree(src_tprog, dst_tprog)
        else:
            raise FileNotFoundError(f"Kansio puuttuu: {src_tprog}. Luo ja täytä treatment_programs initialize-kansioon.")

        # CP-SAT esikäsittely: tuottaa oikeamuotoiset tiedostot
        from cp_sat_preprocessing import (
            cp_sat_generate_batches,
            cp_sat_generate_treatment_programs,
            cp_sat_generate_stations,
            cp_sat_generate_transfer_tasks,
            cp_sat_generate_transporters
        )
        cp_sat_generate_batches(os.path.join(output_dir, "batches.csv"), os.path.join(output_dir, "initialization"))
        cp_sat_generate_treatment_programs(os.path.join(output_dir, "treatment_programs"), os.path.join(output_dir, "initialization"))
        cp_sat_generate_stations(os.path.join(output_dir, "stations.csv"), os.path.join(output_dir, "initialization"))
        cp_sat_generate_transfer_tasks(os.path.join(output_dir, "transfer_tasks.csv"), os.path.join(output_dir, "initialization"))
        cp_sat_generate_transporters(os.path.join(output_dir, "initialization", "transporters_start_positions.csv"), os.path.join(output_dir, "initialization"))

        # Suorita CP-SAT optimointi
        from cp_sat_optimization import cp_sat_optimize
        cp_sat_optimize(output_dir)

    except Exception as e:
        print(f"Virhe simulaation aikana: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
