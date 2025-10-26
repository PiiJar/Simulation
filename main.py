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
from generate_batch_treatment_programs_original import generate_batch_treatment_programs_original
from preprocess_for_cpsat import preprocess_for_cpsat

def initialize_simulation(output_dir):
    """
    Alustaa simulaation luomalla tarvittavat kansiot, käsittelyohjelmat ja esikäsittelemällä datan CP-SAT:ia varten.
    """
    # Luo simulaatiokansio
    output_dir = create_simulation_directory()

    # Luo käsittelyohjelmat
    result = generate_batch_treatment_programs_original(output_dir)
    if not result:
        raise RuntimeError("Käsittelyohjelmien luonti epäonnistui!")

    # Esikäsittele data CP-SAT:ia varten
    preprocess_for_cpsat(output_dir)

    return output_dir

def main():
    """
    Suorittaa simulaattorilogiikan vaiheet alusta loppuun.
    """
    try:
        # Alustus ja esikäsittely
        output_dir = initialize_simulation("output")

        # Alusta loggeri
        from simulation_logger import init_logger
        init_logger(output_dir)

        # CP-SAT optimointi esikäsitellylle datalle
        from run_cpsat_optimization import run_cpsat_optimization
        run_cpsat_optimization(output_dir)

    except Exception as e:
        print(f"Virhe simulaation aikana: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
