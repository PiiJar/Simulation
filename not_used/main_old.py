"""
Main pipeline for production line simulation and optimization

Follows the documented structure:
1. Initialization
2. Preprocessing
3. Optimization / Simulation
4. Results (matrix, transporter movements, visualization, reports)
"""

import os

from create_simulation_directory import create_simulation_directory
from generate_batch_treatment_programs_original import generate_batch_treatment_programs_original
from preprocess_for_cpsat import preprocess_for_cpsat
from cp_sat_stepwise import cp_sat_stepwise, solve_and_save
from generate_matrix_stretched import generate_matrix_stretched
from extract_transporter_tasks import extract_transporter_tasks, create_detailed_movements
from visualize_stretched_matrix import visualize_stretched_matrix
from simulation_logger import init_logger
from generate_production_report import generate_production_report

def main():
    # 1. Initialization
    # Create simulation directory and copy input data
    output_dir = create_simulation_directory()
    generate_batch_treatment_programs_original(output_dir)

    # 2. Preprocessing
    # Transform and validate input data for optimization
    preprocess_for_cpsat(output_dir)

    # 3. Optimization / Simulation
    # Solve production scheduling with CP-SAT model
    model, task_vars, treatment_programs = cp_sat_stepwise(output_dir, hard_order_constraint=True)
    solve_and_save(model, task_vars, treatment_programs, output_dir)

    # 4. Results
    # Generate stretched matrix and transporter movements
    generate_matrix_stretched(output_dir)
    extract_transporter_tasks(output_dir)
    create_detailed_movements(output_dir)

    # Visualization and reporting
    init_logger(output_dir)
    visualize_stretched_matrix(output_dir)
    generate_production_report(output_dir)

    print("[PIPELINE] Simulation and optimization pipeline completed.")

if __name__ == "__main__":

    return output_dir

def main_old():
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
