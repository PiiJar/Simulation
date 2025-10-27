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
    # Luo simulaatiokansio heti alussa
    output_dir = create_simulation_directory()

    # Kopioi initialization-kansio ja kaikki sen sisältö simulaatiokansioon
    import shutil
    init_dir = os.path.join(os.getcwd(), "initialization")
    dst_init = os.path.join(output_dir, "initialization")
    if os.path.exists(dst_init):
        shutil.rmtree(dst_init)
    shutil.copytree(init_dir, dst_init)

    # Luo treatment_programs_original-kansio ja originaalit käsittelyohjelmat vasta kopioinnin jälkeen
    tprog_src_dir = os.path.join(output_dir, "initialization")
    tprog_orig_dir = os.path.join(output_dir, "treatment_programs_original")
    os.makedirs(tprog_orig_dir, exist_ok=True)
    import pandas as pd
    production_path = os.path.join(output_dir, "initialization", "production.csv")
    production = pd.read_csv(production_path)
    for _, row in production.iterrows():
        batch = int(row["Batch"])
        program = int(row["Treatment_program"])
        batch_str = f"{batch:03d}"
        program_str = f"{program:03d}"
        src = os.path.join(tprog_src_dir, f"treatment_program_{program_str}.csv")
        dst = os.path.join(tprog_orig_dir, f"Batch_{batch_str}_Treatment_program_{program_str}.csv")
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            raise FileNotFoundError(f"Käsittelyohjelmatiedosto puuttuu: {src}")
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

        # Kaikki jatkovaiheet käyttävät vain simulaatiokansion initialization-alihakemistoa
        # (ei enää projektin juuren initializationia)

        # Suorita uusi CP-SAT optimointi (nostimen eksplisiittinen malli)
        from cp_sat_transporter_explicit import cp_sat_transporter_explicit
        cp_sat_transporter_explicit(output_dir)

    except Exception as e:
        print(f"Virhe simulaation aikana: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
