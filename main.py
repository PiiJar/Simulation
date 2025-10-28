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
    # --- VAIN VANHAN OPTIMOINNIN (VAPAUSASTE 2) JATKOPUTKI ---
    # Jos halutaan ajaa vain alkuperäisen järjestyksen optimoinnista eteenpäin:
    if os.environ.get("SIM_PIPELINE_FROM_STEP6") == "1":
        print("[PIPELINE] Ajetaan vain vanhan optimoinnin jatkoputki (vaihe 6 eteenpäin, vapausaste 2)")
        # output_dir pitää määrittää tässä polussa
        output_dir = os.environ.get("SIM_OUTPUT_DIR", "output")
        schedule_path2 = os.path.join(output_dir, "logs", "cp-sat-stepwise-schedule.csv")
        df_schedule2 = pd.read_csv(schedule_path2)
        import shutil
        orig_dir = os.path.join(output_dir, "treatment_programs_original")
        opt_dir = os.path.join(output_dir, "treatment_programs_optimized")
        os.makedirs(opt_dir, exist_ok=True)
        for fname in os.listdir(orig_dir):
            if fname.startswith("Batch_") and fname.endswith(".csv"):
                src = os.path.join(orig_dir, fname)
                dst = os.path.join(opt_dir, fname)
                shutil.copy(src, dst)
                # Poista vaihe 0 rivit
                df = pd.read_csv(dst)
                df = df[df["Stage"] != 0]
                import re
                m = re.match(r"Batch_(\d+)_Treatment_program_(\d+)\.csv", fname)
                if m:
                    batch_num = int(m.group(1))
                else:
                    batch_num = None
                for idx, row in df.iterrows():
                    stage = row["Stage"]
                    mask = (df_schedule2["Batch"] == batch_num) & (df_schedule2["Stage"] == stage)
                    if mask.any():
                        duration_sec = int(df_schedule2[mask]["Duration"].values[0])
                        h = duration_sec // 3600
                        m_ = (duration_sec % 3600) // 60
                        s = duration_sec % 60
                        df.at[idx, "CalcTime"] = f"{h:02}:{m_:02}:{s:02}"
                df.to_csv(dst, index=False)
        print(f"[POST] treatment_programs_optimized hakemisto luotu, ohjelmat kopioitu, vaihe 0 rivit poistettu ja CalcTime päivitetty.")

        # Päivitä initialization/production.csv Start_optimized-sarake
        prod_path = os.path.join(output_dir, "initialization", "production.csv")
        if os.path.exists(prod_path):
            df_prod = pd.read_csv(prod_path)
            batch_col = 'Batch' if 'Batch' in df_prod.columns else 'Erä'
            start_opt = []
            for batch in df_prod[batch_col]:
                mask = (df_schedule2["Batch"] == batch) & (df_schedule2["Stage"] == 0)
                if mask.any():
                    end_sec = int(df_schedule2[mask]["End"].values[0])
                    h = end_sec // 3600
                    m = (end_sec % 3600) // 60
                    s = end_sec % 60
                    start_opt.append(f"{h:02}:{m:02}:{s:02}")
                else:
                    start_opt.append("")
            df_prod["Start_optimized"] = start_opt
            def time_to_sec(t):
                if isinstance(t, str) and t and t != "nan":
                    h, m, s = map(int, t.split(":"))
                    return h*3600 + m*60 + s
                return float('inf')
            df_prod = df_prod.copy()
            df_prod["_sortkey"] = df_prod["Start_optimized"].apply(time_to_sec)
            df_prod = df_prod.sort_values("_sortkey").drop(columns=["_sortkey"])
            df_prod.to_csv(prod_path, index=False)
            print(f"[POST] initialization/production.csv päivitetty Start_optimized-sarakkeella ja järjestetty aikajärjestykseen.")

    # Alustus ja esikäsittely (tuottaa output_dir)
    output_dir = initialize_simulation("output")

    # 1. Ratkaise kovalla järjestysrajoitteella (vapausaste 2)
    from cp_sat_stepwise import cp_sat_stepwise, solve_and_save
    import importlib
    # Ladataan cp_sat_stepwise uudelleen, jotta mahdolliset muutokset astuvat voimaan
    importlib.reload(__import__('cp_sat_stepwise'))
    # --- KOVA JÄRJESTYSRAJOITE ---
    # Tee tilapäinen patch: lisää kova järjestysrajoite
    # (Tämä vaatii, että koodi tukee järjestysrajoitteen asettamista parametrilla, muuten vaatii refaktorointia)
    # Oletetaan, että cp_sat_stepwise tukee param: hard_order_constraint
    model2, task_vars2, treatment_programs2 = cp_sat_stepwise(output_dir, hard_order_constraint=True)
    solve_and_save(model2, task_vars2, treatment_programs2, output_dir)
    schedule_path2 = os.path.join(output_dir, "logs", "cp-sat-stepwise-schedule.csv")
    df_schedule2 = pd.read_csv(schedule_path2)
    makespan2 = int(df_schedule2["End"].max())

    # 2. Ratkaise ilman järjestysrajoitetta (vapausaste 3)
    model3, task_vars3, treatment_programs3 = cp_sat_stepwise(output_dir, hard_order_constraint=False)
    solve_and_save(model3, task_vars3, treatment_programs3, output_dir)
    schedule_path3 = os.path.join(output_dir, "logs", "cp-sat-stepwise-schedule.csv")
    df_schedule3 = pd.read_csv(schedule_path3)
    makespan3 = int(df_schedule3["End"].max())

    # 3. Valitse tulos: hyväksy uusi järjestys vain jos makespan paranee
    if makespan3 < makespan2:
        df_schedule = df_schedule3
        print("[VAPAUSASTE 3] Hyväksyttiin uusi järjestys, koska makespan parani.")
    else:
        df_schedule = df_schedule2
        print("[VAPAUSASTE 3] Säilytettiin alkuperäinen järjestys, koska makespan ei parantunut.")

    # Jatka post-prosessointia kuten aiemmin, käyttäen df_schedule
    import shutil
    orig_dir = os.path.join(output_dir, "treatment_programs_original")
    opt_dir = os.path.join(output_dir, "treatment_programs_optimized")
    os.makedirs(opt_dir, exist_ok=True)
    for fname in os.listdir(orig_dir):
        if fname.startswith("Batch_") and fname.endswith(".csv"):
            src = os.path.join(orig_dir, fname)
            dst = os.path.join(opt_dir, fname)
            shutil.copy(src, dst)
            # Poista vaihe 0 rivit
            df = pd.read_csv(dst)
            df = df[df["Stage"] != 0]
            # Päivitä CalcTime schedule-tiedoston Duration-arvolla (muoto hh:mm:ss)
            import re
            m = re.match(r"Batch_(\d+)_Treatment_program_(\d+)\.csv", fname)
            if m:
                batch_num = int(m.group(1))
            else:
                batch_num = None
            for idx, row in df.iterrows():
                stage = row["Stage"]
                mask = (df_schedule["Batch"] == batch_num) & (df_schedule["Stage"] == stage)
                if mask.any():
                    duration_sec = int(df_schedule[mask]["Duration"].values[0])
                    h = duration_sec // 3600
                    m_ = (duration_sec % 3600) // 60
                    s = duration_sec % 60
                    df.at[idx, "CalcTime"] = f"{h:02}:{m_:02}:{s:02}"
            df.to_csv(dst, index=False)
    print(f"[POST] treatment_programs_optimized hakemisto luotu, ohjelmat kopioitu, vaihe 0 rivit poistettu ja CalcTime päivitetty.")

    # Päivitä initialization/production.csv Start_optimized-sarake
    prod_path = os.path.join(output_dir, "initialization", "production.csv")
    if os.path.exists(prod_path):
        df_prod = pd.read_csv(prod_path)
        batch_col = 'Batch' if 'Batch' in df_prod.columns else 'Erä'
        start_opt = []
        for batch in df_prod[batch_col]:
            mask = (df_schedule["Batch"] == batch) & (df_schedule["Stage"] == 0)
            if mask.any():
                end_sec = int(df_schedule[mask]["End"].values[0])
                h = end_sec // 3600
                m = (end_sec % 3600) // 60
                s = end_sec % 60
                start_opt.append(f"{h:02}:{m:02}:{s:02}")
            else:
                start_opt.append("")
        df_prod["Start_optimized"] = start_opt

        def time_to_sec(t):
            if isinstance(t, str) and t and t != "nan":
                h, m, s = map(int, t.split(":"))
                return h*3600 + m*60 + s
            return float('inf')

        df_prod = df_prod.copy()
        df_prod["_sortkey"] = df_prod["Start_optimized"].apply(time_to_sec)
        df_prod = df_prod.sort_values("_sortkey").drop(columns=["_sortkey"])
        df_prod.to_csv(prod_path, index=False)
        print(f"[POST] initialization/production.csv päivitetty Start_optimized-sarakkeella ja järjestetty aikajärjestykseen.")

    # --- Vaihe 6: Luo venytetty matriisi ---
    from generate_matrix_stretched import generate_matrix_stretched
    generate_matrix_stretched(output_dir)
    print("[STEP6] Venytetty matriisi luotu.")


    # --- Vaihe 7: Luo nostintehtävät ja liikkeet ---
    from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
    extract_transporter_tasks(output_dir)
    create_detailed_movements(output_dir)
    print("[STEP7] Nostintehtävät ja liikkeet luotu.")

    # --- Vaihe 8: Visualisoi venytetty matriisi ---
    from visualize_stretched_matrix import visualize_stretched_matrix
    from simulation_logger import init_logger
    init_logger(output_dir)
    visualize_stretched_matrix(output_dir)
    print("[STEP8] Venytetty matriisi visualisoitu.")

    # --- Vaihe 9: Luo tuotantoraportti ---
    from generate_production_report import generate_production_report
    generate_production_report(output_dir)
    print("[STEP9] Tuotantoraportti luotu.")
